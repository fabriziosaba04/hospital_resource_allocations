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


def test_full_universe_of_dry2_claims_and_checker_recall():
    """Owner Point A: every universe claim in every DRY2 explanation, independent of the CHECKER."""
    from collections import Counter
    from pathlib import Path
    spec = Path("results/evaluations/DRY2-HARD10/explanation_claims_full_spec.json")
    out = score("DRY2-HARD10", spec)
    assert len(out["claims"]) == 445
    assert Counter(c["day"] for c in out["claims"]) == {1: 30, 2: 45, 3: 39, 4: 44, 5: 48, 6: 47, 7: 46, 8: 55,
                                                        9: 47, 10: 44}
    assert out["summary"]["ALLOCATOR"] == {"correct": 442, "wrong": 3, "unverifiable": 0}
    assert {c["id"] for c in out["claims"] if c["verdict"] == "wrong"} == {"D2-15", "D2-45", "D7-58"}
    ch = out["checker_on_claims"]
    assert (ch["recall"], ch["precision"]) == ("2/3", "2/3")
    assert ch["wrong_disputes"] == ["D2-14"] and ch["missed"] == ["D7-58"]
