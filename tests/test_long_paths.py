"""Readers of the run folders and the subagent capture work beyond MAX_PATH (Log #117, R56).

R1's two run folders are copied under a root deep enough that every file in them is over 260 characters (R2's
spilled tool results are exactly 260 in the repository). Every reader entry point then runs on the deep copy and
must give the same records, or rewrite its committed output byte for byte. `decisions_ab.main` takes no folder
argument and is not exercised here; its two base folders go through `long_path` like the others.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil

import pytest

from src.evaluation import (adjudication_recall, adjudication_view, claim_review, owner_claims, owner_review_counts,
                            owner_verdicts, rubric_check_view, unverifiable_view)
from src.evaluation.allocator_digest import digest
from src.evaluation.audit import load_records
from src.evaluation.dataset import ROOT
from src.evaluation.run_report import build
from src.mcp_server.consistency import check
from src.mcp_server.store import Store
from src.utils.paths import long_path, walk_files

pytestmark = pytest.mark.skipif(os.name != "nt", reason="MAX_PATH exists only on Windows")

RUN = "R1"
SRC = ROOT / "results"


def _sha(p) -> str:
    return hashlib.sha256(long_path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def deep(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lp")
    shortest_rel = min(len(f"/results/{kind}/{RUN}/{k}") for kind in ("allocations", "evaluations")
                       for k in walk_files(SRC / kind / RUN))
    res = tmp / ("p" * (262 - len(str(tmp.absolute())) - 1 - shortest_rel)) / "results"
    for kind in ("allocations", "evaluations"):
        shutil.copytree(long_path(SRC / kind / RUN), long_path(res / kind / RUN))
    files = walk_files(res)
    shortest = min(len(str(res.absolute() / k)) for k in files)
    assert shortest > 260, shortest                        # every file of the copy is beyond MAX_PATH
    return res


def test_records_and_store_read_at_long_paths(deep):
    alloc = deep / "allocations" / RUN
    assert load_records(alloc) == load_records(SRC / "allocations" / RUN)
    s, ref = Store.from_run_dir(alloc), Store.from_run_dir(SRC / "allocations" / RUN)
    for rec in ("decision_history", "allocation_state", "validation_history", "workflow"):
        assert s.read(rec) == ref.read(rec) and s.read(rec)
    assert s.read_state() == ref.read_state() and s.manifest() == ref.manifest()
    assert check(s) == check(ref) == []


def test_digest_and_run_report_rewrite_committed_files_at_long_paths(deep):
    ev = deep / "evaluations" / RUN
    shutil.rmtree(long_path(ev / "allocator_digest"))
    assert len(digest(RUN, deep)) == 30
    build(RUN, deep)
    for k, p in walk_files(SRC / "evaluations" / RUN / "allocator_digest").items():
        assert _sha(ev / "allocator_digest" / k) == _sha(p), k
    assert _sha(ev / "run_report.json") == _sha(SRC / "evaluations" / RUN / "run_report.json")


def test_owner_review_entry_points_at_long_paths(deep):
    ev, alloc = deep / "evaluations" / RUN, deep / "allocations" / RUN
    before = {k: _sha(p) for k, p in walk_files(ev).items()}
    owner_claims.main(RUN, ev, alloc)
    claim_review.main(RUN, ev)
    owner_verdicts.main(RUN, ev, alloc)
    adjudication_recall.main(RUN, ev, alloc)
    adjudication_view.main(RUN, ev, alloc)
    rubric_check_view.main(RUN, ev, alloc)
    unverifiable_view.main(RUN, ev, alloc)
    counts = owner_review_counts.main(RUN, ev)
    assert counts == owner_review_counts.main(RUN, SRC / "evaluations" / RUN)
    after = {k: _sha(p) for k, p in walk_files(ev).items()}
    assert after == before                                 # every output rewritten byte for byte, nothing new
    assert json.loads(long_path(ev / "run_report.json").read_text(encoding="utf-8"))["run_id"] == RUN


def test_long_path_collapses_dot_dot_and_is_idempotent(tmp_path):
    (tmp_path / "b").write_text("x")
    p = long_path(tmp_path / "a" / ".." / "b")             # the extended form would not resolve ".." itself
    assert str(p).startswith("\\\\?\\") and ".." not in str(p) and p.read_text() == "x"
    assert long_path(p) == p
