"""Clone procedure (owner decision §11 #44): a run folder copied back from a clone gives a byte-identical run
report; everything the run wrote is copied and hash-checked; the launcher refuses synced folders."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.evaluation.dataset import ROOT
from src.mcp_server import launch
from src.mcp_server.copy_back import copy_back
from src.mcp_server.store import Store

RUN = "DRY2-HARD10"
FIX = ROOT / "results" / "dry_runs" / "HARD10_fixture"


def _fake_clone(tmp: Path, lose_data_root: bool = False) -> Path:
    clone = tmp / "clone"
    for kind in ("allocations", "evaluations"):
        shutil.copytree(ROOT / "results" / kind / RUN, clone / "results" / kind / RUN)
    (clone / "results" / "evaluations" / RUN / "run_report.json").unlink()   # must be rebuilt, not copied
    if lose_data_root:                                                        # the clone was deleted
        mp = clone / "results" / "allocations" / RUN / "run_manifest.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["data_root"] = str(tmp / "deleted_clone")
        mp.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8", newline="\n")
    return clone


@pytest.mark.parametrize("lose_data_root", [False, True])
def test_copied_run_rebuilds_a_byte_identical_report(tmp_path, lose_data_root):
    clone = _fake_clone(tmp_path, lose_data_root)
    repo = tmp_path / "repo" / "results"
    out = copy_back(clone, RUN, repo_results=repo, data_root=FIX if lose_data_root else None)
    assert out["hash_mismatches"] == [] and out["consistency_problems"] == [] and out["run_report_rebuilt"]
    want = (ROOT / "results" / "evaluations" / RUN / "run_report.json").read_bytes()
    assert (repo / "evaluations" / RUN / "run_report.json").read_bytes() == want
    # everything the run wrote came back, transcripts and process calls included
    for rel in ("allocations/DRY2-HARD10/transcripts/launch-1.jsonl", "allocations/DRY2-HARD10/launches.jsonl",
                "allocations/DRY2-HARD10/state.json", "evaluations/DRY2-HARD10/process_calls.jsonl",
                "evaluations/DRY2-HARD10/validation_history.jsonl"):
        assert (repo / rel).is_file()
    assert "transcripts/launch-1.jsonl" in out["files"]["allocations"]


def test_copy_back_never_overwrites(tmp_path):
    clone = _fake_clone(tmp_path)
    repo = tmp_path / "repo" / "results"
    copy_back(clone, RUN, repo_results=repo)
    with pytest.raises(SystemExit, match="never overwritten"):
        copy_back(clone, RUN, repo_results=repo)


def test_store_paths_resolve_relative_to_the_run_folder(tmp_path):
    clone = _fake_clone(tmp_path)
    s = Store.from_run_dir(clone / "results" / "allocations" / RUN)
    assert s.eval_dir == (clone / "results" / "evaluations" / RUN).resolve()
    assert s.read("validation_history")                 # the manifest's absolute eval_dir is not used


def test_launcher_refuses_synced_folders(tmp_path, monkeypatch):
    assert launch.synced_folder(Path(r"C:\Users\x\OneDrive\Documenti\repo")) == "onedrive"
    assert launch.synced_folder(Path(r"C:\Users\x\Dropbox\repo")) == "dropbox"
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.delenv("OneDriveConsumer", raising=False)
    monkeypatch.delenv("OneDriveCommercial", raising=False)
    assert launch.synced_folder(tmp_path) is None

    def store_for(dataset):
        d = tmp_path / "onedrive_like" / "OneDrive" / "results" / "allocations" / dataset
        d.mkdir(parents=True, exist_ok=True)
        (d / "run_manifest.json").write_text(json.dumps({"dataset_id": dataset}), encoding="utf-8")
        return Store(d, d)

    monkeypatch.setattr(launch, "ROOT", tmp_path / "OneDrive" / "repo")
    with pytest.raises(SystemExit, match="synced folder"):
        launch.guard(store_for("seed20261107"))
    with pytest.raises(SystemExit, match="synthetic fixtures only"):
        launch.guard(store_for("seed20261107"), allow_synced=True)          # frozen data: never allowed
    with pytest.raises(SystemExit, match="synced folder"):
        launch.guard(store_for("HARD10"))
    assert launch.guard(store_for("HARD10"), allow_synced=True) == "onedrive"   # dry runs, if allowed
    monkeypatch.setattr(launch, "ROOT", tmp_path / "clone")
    clean = tmp_path / "clean" / "results" / "allocations" / "seed20261107"
    clean.mkdir(parents=True)
    (clean / "run_manifest.json").write_text(json.dumps({"dataset_id": "seed20261107"}), encoding="utf-8")
    assert launch.guard(Store(clean, clean)) is None


def test_launcher_counts_refused_subagent_spawns():
    """Log #94: a run whose role server did not connect must not look like a clean launch."""
    line = json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content":
            "Agent 'allocator' would be spawned with zero tools — refusing."}]}})
    assert launch.spawn_refusals([line, line, "{}"]) == 2
    assert launch.spawn_refusals(["{}"]) == 0
