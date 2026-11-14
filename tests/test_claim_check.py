"""Claim-by-claim verification (owner decision §11 #48): DRY2's two explanation findings are the first case."""

from __future__ import annotations

from src.evaluation.claim_check import score


def test_dry2_findings_scored_claim_by_claim():
    out = score("DRY2-HARD10")
    v = {c["id"]: c["verdict"] for c in out["claims"]}
    # finding 1: the ALLOCATOR's "no better" is wrong (6.0 vs 5.6 need covered at levels 2-3); the CHECKER's
    # three figures are right
    assert (v["F1-A1"], v["F1-A2"]) == ("correct", "wrong")
    assert (v["F1-C1"], v["F1-C2"], v["F1-C3"]) == ("correct", "correct", "correct")
    # finding 2: one correct ALLOCATOR figure (5 level-3 overflow), one wrong (4 empty beds, really 5),
    # and one wrong dispute by the CHECKER (it called the correct level-3 figure wrong)
    assert (v["F2-A1"], v["F2-A2"]) == ("correct", "wrong")
    assert (v["F2-C1"], v["F2-C2"]) == ("wrong", "correct")
    assert {c["id"]: c["computed"] for c in out["claims"]}["F2-A2"] == 5
    assert out["summary"] == {"ALLOCATOR": {"correct": 2, "wrong": 2, "unverifiable": 0},
                              "CHECKER": {"correct": 4, "wrong": 1, "unverifiable": 0}}
    assert all(f["finding_valid"] for f in out["findings"].values())
