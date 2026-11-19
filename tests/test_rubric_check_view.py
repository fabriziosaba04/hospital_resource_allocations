"""Display file for the owner's check of the rubric-dependent wrong claims."""

from __future__ import annotations

import csv

from src.evaluation.dataset import ROOT
from src.evaluation.rubric_check_view import sentence

EVAL = ROOT / "results" / "evaluations" / "R1"


def test_sentence_handles_elided_quotes():
    t = "Beds are above occupied (1/2); the 9 spare beds are weighted toward IM. Next one."
    s, i, j = sentence(t, "the 9 spare beds are weighted toward ...")
    assert s == "Beds are above occupied (1/2); the 9 spare beds are weighted toward IM."   # no split before lowercase
    assert s[i:j] == "the 9 spare beds are weighted toward"


def test_committed_view_and_verdicts():
    rows = list(csv.DictReader(open(EVAL / "owner_review" / "rubric_dependent_54_check.csv",
                                    encoding="utf-8-sig").readlines()[1:]))
    assert len(rows) == 54 and all(r["full_sentence"] != "(not found)" for r in rows)
    assert sum(bool(r["qualifiers_in_sentence"]) for r in rows) == 20
    assert not any("inside" in r["qualifiers_in_sentence"] for r in rows)
    own = {r["id"]: r["owner_verdict"] for r in csv.DictReader(open(EVAL / "owner_review" / "owner_review_wrong.csv",
                                                                     encoding="utf-8-sig"))}
    assert sum(v == "confirmed_wrong" for v in own.values()) == 19
    assert {i for i, v in own.items() if v == "extraction_error"} == {"R1-D28-05", "R1-D28-06"}
    assert not any(own[r["id"]] for r in rows)                      # the 54 are still pending
