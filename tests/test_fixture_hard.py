"""The hard synthetic fixture HARD10 contains every situation it is meant to guarantee (owner decision §11 #41).

Allocation-dependent conditions are shown under the deterministic baselines: a conflict that arises under
B0 (no reallocation) or B2 (proportional) and that B1 (priority-first) avoids is an avoidable decision the
ALLOCATOR faces. The forced cut is shown by a policy-independent bound.
"""

from __future__ import annotations

from collections import Counter

import pytest

from src.environment.nurses import requirement
from src.evaluation.audit import audit_run, read_jsonl
from src.evaluation.dataset import load_dataset
from src.evaluation.runner import run_baseline
from src.mcp_server import fixture_hard as fh
from src.utils.constants import DEPARTMENTS


@pytest.fixture(scope="module")
def hard(tmp_path_factory):
    root = tmp_path_factory.mktemp("hard")
    fh.write_fixture(root)
    ds = load_dataset(fh.DATASET_ID, root)
    runs = {}
    for b in ("B0", "B1", "B2"):
        rd = run_baseline(b, ds, root / "res")
        runs[b] = (rd, audit_run(ds, rd)[1])
    return ds, runs


def _pairs(days, kind=None):
    return {(p["unserved_level"], p["served_level"]) for d in days for p in d["pairs"]
            if kind is None or p["kind"] == kind}


def test_is_synthetic_and_independent_of_frozen_data():
    assert fh.DATASET_ID == "HARD10" and fh.SEED == 20261114
    assert fh.SEED not in (20261107, 20261108, 20261109)
    src = open(fh.__file__, encoding="utf-8").read()
    assert "data_generation" not in src.replace("src/data_generation/`", "")   # own generator, no import
    assert "seed2026110" not in src


def test_cross_department_priority_conflicts(hard):
    """L3 vs L1 and L2 vs L1: a waiting patient in a department with room, a movable bed elsewhere given to
    an L1 patient. Arises under B0 or B2; B1 shows it was avoidable."""
    _, runs = hard
    displaced = _pairs(runs["B0"][1], "displaced") | _pairs(runs["B2"][1], "displaced")
    assert (3, 1) in displaced and (2, 1) in displaced
    assert not _pairs(runs["B1"][1])


def test_same_level_waiting_in_different_departments(hard):
    ds, runs = hard
    rd, days = runs["B0"]
    bed = {x["day"]: x for x in read_jsonl(rd / "bed_assignment_state.jsonl") if x["stage"] == "final"}
    lvl = {p.patient_id: p.complexity for t in range(1, ds.horizon + 1) for p in ds.present(t)}
    multi = [t for t in bed if any(len({v["department"] for pid, v in bed[t]["patients"].items()
                                        if v["status"] == "overflow" and lvl[pid] == k}) >= 2 for k in (1, 2, 3))]
    assert len(multi) >= 2
    assert sum(len(d["f1_inversions"]) for d in days) > 0               # and F1 inversions arise under B0
    assert sum(len(d["f1_inversions"]) for d in runs["B2"][1]) > 0


def test_nurse_rationing_on_several_days(hard):
    ds, _ = hard
    short = []
    for t in range(1, ds.horizon + 1):
        c = Counter((p.department, p.complexity) for p in ds.present(t))
        req = sum(requirement(c[(d, 1)], c[(d, 2)], c[(d, 3)], ds.env) for d in DEPARTMENTS)
        short.append(req > ds.pool_nurses[t])
    assert sum(short) >= 3


def test_forced_shock_cut(hard):
    """Day 8: any allocation that fills every bed on day 7 leaves more holders than the day-8 pool, because
    at most the day-7 patients discharged on day 8 can free a bed. B1 and B2 (which fill beds) are shock days."""
    ds, runs = hard
    present7 = ds.present(7)
    assert len(present7) >= ds.pool_beds[7]                              # every bed can be filled on day 7
    still = {p.patient_id for p in ds.present(8)}
    leaving = sum(1 for p in present7 if p.patient_id not in still)
    assert ds.pool_beds[7] - leaving > ds.pool_beds[8]
    for b in ("B1", "B2"):
        assert [d["day"] for d in runs[b][1] if d["shock_day"]] == [8]


def test_pool_increase_and_restore(hard):
    ds, _ = hard
    b = [ds.pool_beds[t] for t in range(1, ds.horizon + 1)]
    n = [ds.pool_nurses[t] for t in range(1, ds.horizon + 1)]
    assert b[3] > b[2] and n[3] > n[2]                                   # increase on day 4
    assert b[5] == b[0] and n[5] == n[0]                                 # restore on day 6
    assert b[7] < b[6] and b[9] == b[0]                                  # cut on day 8, restore on day 10


def test_workflow_runs_on_the_hard_fixture(tmp_path):
    """The server's state machine handles the cut day (repair fallback on every day, no LLM)."""
    from src.mcp_server.init_run import init_run
    from src.mcp_server.workflow import Workflow
    fh.write_fixture(tmp_path)
    w = Workflow(init_run(fh.DATASET_ID, "H1", data_root=tmp_path, results_root=tmp_path / "results",
                          check_manifest=False, set_pointer=False))
    for t in range(1, fh.HORIZON + 1):
        w.advance_day()
        w.end_allocation_phase()
        if t % 5 == 0:
            w.submit_validation_report({"period": {"from_day": t - 4, "to_day": t}, "checked": ["x"],
                                        "issues": [], "summary": "test"})
            ref = w.checker_allocation_state()["reference_allocations"]
            assert len(ref) == 5
        w.close_day()
    assert w.get_workflow_status()["phase"] == "FINISHED"
