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


def _fake_projects(tmp: Path, session_id: str) -> Path:
    s = tmp / "projects" / "C--clone" / session_id
    (s / "subagents").mkdir(parents=True)
    (s / "tool-results").mkdir()
    for name, kind in (("a1", "allocator"), ("c1", "checker")):
        (s / "subagents" / f"agent-{name}.meta.json").write_text(json.dumps({"agentType": kind}))
        (s / "subagents" / f"agent-{name}.jsonl").write_text(json.dumps({"type": "user"}) + "\n")
    (s / "tool-results" / "mcp-allocator-x-1.txt").write_text("big")
    return tmp / "projects"


def _session_ids(clone: Path) -> list[str]:
    import re
    t = (clone / "results" / "allocations" / RUN / "transcripts" / "launch-1.jsonl").read_text(encoding="utf-8")
    return list(dict.fromkeys(re.findall(r'"session_id":"([0-9a-f-]{36})"', t)))


def test_copy_back_captures_subagent_transcripts(tmp_path):
    """R40: the session folder Claude Code wrote outside the run folder is captured and hash-checked."""
    clone = _fake_clone(tmp_path)
    (sid,) = _session_ids(clone)
    repo = tmp_path / "repo" / "results"
    out = copy_back(clone, RUN, repo_results=repo, projects=_fake_projects(tmp_path, sid))
    st = out["subagent_transcripts"]
    assert st["problems"] == [] and st["hash_mismatches"] == []
    assert st["by_folder"] == {"allocator": 3, "checker": 2, "unclassified": 0}
    sub = repo / "allocations" / RUN / "transcripts" / "subagents"
    assert (sub / "allocator" / "agent-a1.jsonl").is_file() and (sub / "SHA256SUMS.json").is_file()


def test_copy_back_flags_a_missing_session_folder(tmp_path):
    clone = _fake_clone(tmp_path)
    repo = tmp_path / "repo" / "results"
    out = copy_back(clone, RUN, repo_results=repo, projects=tmp_path / "empty_projects")
    st = out["subagent_transcripts"]
    assert st["preserved_files"] == 0 and len(st["problems"]) == 1 and "no session folder" in st["problems"][0]


def test_copy_back_resume_completes_a_partial_attempt(tmp_path):
    """Log #116, R56: the state R2's failed copy-back left (run folders copied, capture stopped in tool-results,
    no SHA256SUMS.json, no run report, no copy_back.json) is completed by --resume and only by --resume."""
    clone = _fake_clone(tmp_path)
    (sid,) = _session_ids(clone)
    projects = _fake_projects(tmp_path, sid)
    repo = tmp_path / "repo" / "results"
    first = copy_back(clone, RUN, repo_results=repo, projects=projects)
    sub = repo / "allocations" / RUN / "transcripts" / "subagents"
    for p in (sub / "SHA256SUMS.json", sub / "allocator" / "tool-results" / "mcp-allocator-x-1.txt",
              repo / "evaluations" / RUN / "copy_back.json", repo / "evaluations" / RUN / "run_report.json"):
        p.unlink()
    with pytest.raises(SystemExit, match="never overwritten"):
        copy_back(clone, RUN, repo_results=repo, projects=projects)
    out = copy_back(clone, RUN, repo_results=repo, projects=projects, resume=True)
    st = out["subagent_transcripts"]
    assert out["hash_mismatches"] == [] and out["consistency_problems"] == [] and out["run_report_rebuilt"]
    assert st["problems"] == [] and st["hash_mismatches"] == [] and st["by_folder"] == first["subagent_transcripts"]["by_folder"]
    assert out["resumed"] == {"run_folders_verified_in_place": ["allocations", "evaluations"]}
    assert out["files"] == first["files"]
    with pytest.raises(SystemExit, match="complete"):
        copy_back(clone, RUN, repo_results=repo, projects=projects, resume=True)


def test_copy_back_resume_refuses_a_run_folder_that_differs_from_the_clone(tmp_path):
    clone = _fake_clone(tmp_path)
    repo = tmp_path / "repo" / "results"
    copy_back(clone, RUN, repo_results=repo, projects=tmp_path / "empty_projects")
    (repo / "evaluations" / RUN / "copy_back.json").unlink()
    (repo / "evaluations" / RUN / "run_report.json").unlink()
    state = repo / "allocations" / RUN / "state.json"
    state.write_text(state.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not match the clone"):
        copy_back(clone, RUN, repo_results=repo, projects=tmp_path / "empty_projects", resume=True)
