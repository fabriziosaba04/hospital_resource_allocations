"""Descriptive claim accuracy after owner review (§11 #68) and the unverifiable review view."""

from __future__ import annotations

import csv

from src.evaluation import owner_review_counts
from src.evaluation.dataset import ROOT
from src.evaluation.unverifiable_view import AB, reason

EVAL = ROOT / "results" / "evaluations" / "R1"


def test_descriptive_count_next_to_primary(tmp_path):
    import shutil
    ev = tmp_path / "R1"
    (ev / "owner_review").mkdir(parents=True)
    shutil.copy(EVAL / "explanation_claims.json", ev)
    for n in ("owner_review_wrong.csv", "owner_review_unverifiable.csv"):
        shutil.copy(EVAL / "owner_review" / n, ev / "owner_review")
    r = owner_review_counts.main("R1", ev)
    assert r["pre_registered"]["total"] == {"correct": 948, "wrong": 75, "unverifiable": 26}
    assert r["after_owner_review"]["total"] == {"correct": 1015, "wrong": 19, "unverifiable": 15}     # §11 #69
    assert r["provisional"] is False and r["pending_owner_verdicts"] == {"wrong": 0, "unverifiable": 0}


def test_unverifiable_view():
    assert AB["cardiology"] == "CA" and AB["internal_medicine"] == "IM"          # by name, not by order (R54)
    assert reason("x fails validation (EVICTION): unverifiable; also a vague qualifier") == \
        "alternative fails validation; also vague qualifier"
    rows = {r["id"]: r for r in csv.DictReader(open(EVAL / "owner_review" / "unverifiable_26_check.csv",
                                                     encoding="utf-8-sig").readlines()[1:])}
    assert len(rows) == 26
    assert (rows["R1-D30-47"]["value"], rows["R1-D30-48"]["value"]) == ("29", "28")    # the ALLOCATOR's 29 / 28
    assert rows["R1-D19-23"]["value"] == "0.2"
