"""Resume, HALTED and stale-lock behaviour (owner decision §11 #33).

The resume tests kill a run process abruptly part-way through a day (after its n-th append to a given
record, before the remaining writes of that step), resume it in a new process, and check that the
records are consistent, that no day is duplicated, and that they equal an uninterrupted run's.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from src.mcp_server.consistency import check
from src.mcp_server.fixture import DATASET_ID, write_fixture
from src.mcp_server.init_run import init_run
from src.mcp_server.store import Store, StoreError
from src.mcp_server.workflow import Workflow, WorkflowError

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests" / "resume_driver.py"
RECORDS = ("observed_state", "allocation_state", "decision_history", "bed_assignment_state",
           "deterministic_audit", "validation_history")
VOLATILE = {"created_at", "recovered", "run_id"}    # run_id differs by construction


def _drive(store: Store, crash: str | None = None) -> int:
    env = dict(os.environ)
    env.pop("HRA_CRASH_AFTER", None)
    if crash:
        env["HRA_CRASH_AFTER"] = crash
    return subprocess.run([sys.executable, str(DRIVER), str(store.alloc_dir), str(store.eval_dir)],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=300).returncode


def _new_run(root: Path, run_id: str) -> Store:
    return init_run(DATASET_ID, run_id, data_root=root, results_root=root / "results", check_manifest=False,
                    set_pointer=False)


def _canonical(store: Store) -> dict:
    return {r: [{k: v for k, v in x.items() if k not in VOLATILE} for x in store.read(r)] for r in RECORDS}


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    root = tmp_path_factory.mktemp("ref")
    write_fixture(root)
    store = _new_run(root, "REF")
    assert _drive(store) == 0
    assert check(store) == []
    return root, _canonical(store)


# crash points: (record, n-th append in the crashing process); together they cut every write sequence
CRASHES = ["observed_state:1", "observed_state:3", "allocation_state:1", "allocation_state:3",
           "decision_history:2", "decision_history:3", "bed_assignment_state:2", "bed_assignment_state:5",
           "deterministic_audit:1", "validation_history:1", "workflow:4", "workflow:9"]


@pytest.mark.parametrize("crash", CRASHES)
def test_kill_mid_day_and_resume_gives_the_same_records(reference, crash):
    root, ref = reference
    store = _new_run(root, "C-" + crash.replace(":", "-"))
    assert _drive(store, crash) == 17                      # killed part-way, without cleanup
    assert store.read_state()["phase"] != "FINISHED"
    assert _drive(store) == 0                              # a new process resumes from the records
    assert check(store) == []
    assert _canonical(store) == ref


def test_consistency_check_detects_a_duplicated_day(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "DUP")
    assert _drive(store) == 0
    line = store.read("observed_state")[2]
    with store.lock():
        store.append("observed_state", line)
    assert any("observed_state: 2 lines for day 3" in p for p in check(store))


def test_unexpected_error_halts_with_a_recorded_reason(tmp_path, monkeypatch):
    write_fixture(tmp_path)
    w = Workflow(_new_run(tmp_path, "HALT"))
    w.advance_day()
    monkeypatch.setattr(w, "_write_beds", lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone")))
    with pytest.raises(WorkflowError, match="halted"):
        w.end_allocation_phase()
    st = w.get_workflow_status()
    assert st["phase"] == "HALTED" and "disk gone" in st["expected_next_action"]
    s = w.store.read_state()
    assert "OSError: disk gone" in s["halt_reason"] and s["phase_before_halt"] == "ALLOCATION"
    assert [x for x in w.store.read("workflow") if x["event"] == "halted"][0]["reason"] == s["halt_reason"]
    with pytest.raises(WorkflowError, match="halted"):
        w.close_day()
    assert not (w.store.alloc_dir / ".lock").exists()


def test_phase_errors_do_not_halt(tmp_path):
    write_fixture(tmp_path)
    w = Workflow(_new_run(tmp_path, "NOHALT"))
    with pytest.raises(WorkflowError):
        w.close_day()
    assert w.store.read_state()["phase"] == "READY"


def test_lock_of_a_dead_process_is_broken_and_logged(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "LOCK1")
    dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True,
                          text=True).stdout.strip()
    (store.alloc_dir / ".lock").write_text(json.dumps({"pid": int(dead), "t": time.time()}))
    t0 = time.monotonic()
    with store.lock(timeout=5):
        pass
    assert time.monotonic() - t0 < 2
    breaks = (store.alloc_dir / "lock_breaks.jsonl").read_text().splitlines()
    assert json.loads(breaks[0])["reason"] == "holder process gone"


def test_fresh_lock_of_a_live_process_is_respected(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "LOCK2")
    (store.alloc_dir / ".lock").write_text(json.dumps({"pid": os.getpid(), "t": time.time()}))
    with pytest.raises(StoreError, match="held"):
        with store.lock(timeout=0.5):
            pass
    assert not (store.alloc_dir / "lock_breaks.jsonl").exists()


def test_old_lock_is_broken_even_if_its_process_lives(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "LOCK3")
    (store.alloc_dir / ".lock").write_text(json.dumps({"pid": os.getpid(), "t": time.time() - 3600}))
    with store.lock(timeout=5):
        pass
    assert json.loads((store.alloc_dir / "lock_breaks.jsonl").read_text().splitlines()[0])["reason"] == \
        "older than limit"


def test_torn_last_line_is_ignored(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "TORN")
    w = Workflow(store)
    w.advance_day()
    with open(store.path("observed_state"), "a", encoding="utf-8") as f:
        f.write('{"run_id": "TORN", "day": 2, "obs')          # a write cut off by a kill
    assert len(store.read("observed_state")) == 1


def test_append_after_a_torn_line_starts_a_new_line(tmp_path):
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "TORN2")
    w = Workflow(store)
    w.advance_day()
    with open(store.path("workflow"), "a", encoding="utf-8") as f:
        f.write('{"run_id": "TORN2", "da')
    n = len(store.read("workflow"))
    w.end_allocation_phase()
    assert len(store.read("workflow")) > n and check(store) == []


def test_kill_between_accepted_decision_and_allocation_line_is_recovered(tmp_path):
    """decision_history:3 is day 2's accepted attempt; the process dies before its allocation line."""
    write_fixture(tmp_path)
    store = _new_run(tmp_path, "RECOVER")
    assert _drive(store, "decision_history:3") == 17
    acc = [x for x in store.read("decision_history") if x["day"] == 2 and x["outcome"] == "accepted"]
    assert acc and not [x for x in store.read("allocation_state") if x["day"] == 2 and x["source"] == "ALLOCATOR"]
    assert _drive(store) == 0
    rec = [x for x in store.read("allocation_state") if x["day"] == 2 and x["source"] == "ALLOCATOR"]
    assert len(rec) == 1 and rec[0].get("recovered") is True and rec[0]["beds"] == acc[0]["beds"]
    assert any(x["event"] == "recovered_allocation_line" for x in store.read("workflow"))
    assert check(store) == []
