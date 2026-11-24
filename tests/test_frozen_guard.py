"""Frozen run folders are read-only (owner decision 2026-11-23; REFLECTION_LOG R59-R61).

A run whose `results/evaluations/<run>/copy_back.json` exists is frozen evidence: every writer in src/ calls
`guard_write`, which refuses any write into `results/{allocations,evaluations}/<run>/`; copy-back is the only
writer allowed there, because it runs before `copy_back.json` exists. Recomputations default to
`results/analysis/recomputed/<run_id>/`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from src.evaluation.dataset import ROOT, load_dataset
from src.evaluation.metrics import evaluate_run
from src.evaluation.run_report import build
from src.mcp_server.copy_back import copy_back
from src.mcp_server.store import Store
from src.utils import paths
from src.utils.paths import FrozenRunError, frozen_run_of, guard_write

DEV = ROOT / "results" / "development"
FIX = DEV / "dry_runs" / "HARD10_fixture"
RUN = "DRY2-HARD10"


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    """A results root holding DRY2 as a frozen run (a copy_back.json in its evaluation folder)."""
    res = tmp_path / "repo" / "results"
    for kind in ("allocations", "evaluations"):
        shutil.copytree(DEV / kind / RUN, res / kind / RUN)
    (res / "evaluations" / RUN / "copy_back.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(paths, "RESULTS_ROOT", res)
    return res


def test_guard_classifies_paths(frozen):
    assert frozen_run_of(frozen / "allocations" / RUN / "state.json") == RUN
    assert frozen_run_of(frozen / "evaluations" / RUN.lower() / "x" / "y.json") == RUN      # case-insensitive
    assert frozen_run_of(paths.long_path(frozen / "evaluations" / RUN / "a.json")) == RUN   # extended form
    assert frozen_run_of(frozen / "evaluations" / "B0-seed20261107" / "metrics.json") is None
    assert frozen_run_of(frozen / "evaluations" / "headroom.json") is None
    assert frozen_run_of(frozen / "analysis" / "recomputed" / RUN / "metrics.json") is None
    assert frozen_run_of(frozen.parent / "elsewhere" / "evaluations" / RUN / "x") is None   # outside the root
    with pytest.raises(FrozenRunError, match="frozen run folder"):
        guard_write(frozen / "evaluations" / RUN)


def test_recomputation_into_a_frozen_run_is_refused(frozen):
    before = _hashes(frozen)
    ds = load_dataset("HARD10", FIX)
    alloc, ev = frozen / "allocations" / RUN, frozen / "evaluations" / RUN
    with pytest.raises(FrozenRunError):
        evaluate_run(ds, alloc, out_root=frozen / "evaluations")
    with pytest.raises(FrozenRunError):
        build(RUN, frozen, data_root=FIX, out_dir=ev)
    with pytest.raises(FrozenRunError):
        Store.from_run_dir(alloc).append("workflow", {"x": 1})
    assert _hashes(frozen) == before                       # nothing in the frozen run changed
    # the defaults go to results/analysis/recomputed/<run_id>/ and succeed
    evaluate_run(ds, alloc)
    build(RUN, frozen, data_root=FIX)
    out = frozen / "analysis" / "recomputed" / RUN
    assert {p.name for p in out.iterdir()} == {"deterministic_audit.jsonl", "metrics.json", "run_report.json"}
    committed = DEV / "evaluations" / RUN / "run_report.json"
    assert (out / "run_report.json").read_bytes() == committed.read_bytes()
    assert {k: v for k, v in _hashes(frozen).items() if not k.startswith("analysis")} == before


def test_copy_back_still_works_and_then_freezes_the_run(tmp_path, monkeypatch):
    clone = tmp_path / "clone"
    for kind in ("allocations", "evaluations"):
        shutil.copytree(DEV / kind / RUN, clone / "results" / kind / RUN)
    (clone / "results" / "evaluations" / RUN / "run_report.json").unlink()
    repo = tmp_path / "repo" / "results"
    other = repo / "evaluations" / "R9"                     # another run, already frozen, in the same root
    other.mkdir(parents=True)
    (other / "copy_back.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(paths, "RESULTS_ROOT", repo)
    out = copy_back(clone, RUN, repo_results=repo, data_root=FIX, projects=tmp_path / "no_projects")
    assert out["hash_mismatches"] == [] and out["run_report_rebuilt"]
    assert (repo / "evaluations" / RUN / "copy_back.json").is_file()
    assert (repo / "evaluations" / RUN / "run_report.json").read_bytes() == \
        (DEV / "evaluations" / RUN / "run_report.json").read_bytes()
    with pytest.raises(FrozenRunError):                     # once copied back, the run is frozen
        build(RUN, repo, data_root=FIX, out_dir=repo / "evaluations" / RUN)


WRITE = re.compile(r"\.write_text\(|\.write_bytes\(|open\([^)]*[\"'](?:w|a|x)b?[\"']|shutil\.copy|copytree\(|"
                   r"os\.replace\(|\.mkdir\(")
EXEMPT = {"src/mcp_server/copy_back.py",                     # copy-back: the one writer allowed into run folders
          "src/mcp_server/fixture.py", "src/mcp_server/fixture_hard.py",   # write synthetic fixtures under a root
          "src/utils/paths.py"}


def test_every_writer_in_src_calls_the_guard():
    """R60: coverage comes from a search of the code, not from a list of modules."""
    missing = []
    for p in sorted((ROOT / "src").rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("src/data_generation/") or rel in EXEMPT:   # data/ is guarded by the manifest
            continue
        text = p.read_text(encoding="utf-8")
        if WRITE.search(text) and "guard_write" not in text:
            missing.append(rel)
    assert missing == []


OWNER_REVIEW = ("owner_claims", "claim_review", "owner_verdicts", "decisions_ab", "adjudication_recall",
                "adjudication_view", "rubric_check_view", "unverifiable_view", "owner_review_counts")


def test_owner_review_output_root(frozen):
    """Log #127: the owner-review modules write under `out_dir`, else the evaluation folder the caller passed
    (a copy, in tests), else results/analysis/recomputed/<run>/; never into a frozen run folder."""
    other = frozen.parent / "elsewhere"
    assert paths.review_out_dir(RUN, out_dir=other) == paths.long_path(other)
    assert paths.review_out_dir(RUN, eval_dir=other) == paths.long_path(other)
    assert paths.review_out_dir(RUN) == paths.long_path(frozen / "analysis" / "recomputed" / RUN)
    for bad in ({"out_dir": frozen / "evaluations" / RUN}, {"eval_dir": frozen / "evaluations" / RUN}):
        with pytest.raises(FrozenRunError):
            paths.review_out_dir(RUN, **bad)


def test_owner_review_modules_take_an_output_root():
    import importlib
    import inspect
    for name in OWNER_REVIEW:
        mod = importlib.import_module(f"src.evaluation.{name}")
        assert "out_dir" in inspect.signature(mod.main).parameters, name
        assert '"--out"' in inspect.getsource(mod), name
