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


def test_stratification_of_dry2_wrong_claims():
    """Owner review 2026-11-14 (Q1, Q3): basis and rubric dependence of the three wrong claims."""
    from pathlib import Path
    out = score("DRY2-HARD10", Path("results/evaluations/DRY2-HARD10/explanation_claims_full_spec.json"))
    st = out["stratified"]
    assert st["allocator_by_basis"]["derived"] == {"correct": 0, "wrong": 3, "unverifiable": 0}
    alt = {c["id"]: (c.get("verdict_alternative"), c.get("computed_alternative")) for c in out["claims"]}
    # D7-58: the bed was spare (1), not empty (0): wrong only under the strict reading of "empty"
    assert alt["D7-58"] == ("correct", 1)
    # D2-15: 5 empty, 6 spare, stated 4: wrong under either reading, so arithmetic, not semantic
    assert alt["D2-15"] == ("wrong", 6)
    # D2-45 "no better" (§11 #57): the alternative is better at tier 2 (6.0 vs 5.6, tier 3 tied at 5.6), so wrong
    # lexicographically; the rival reading (need covered at levels 2-3 summed) gives 6.0 vs 5.6, wrong too
    d245 = next(c for c in out["claims"] if c["id"] == "D2-45")
    assert (d245["computed"], d245["computed_compare"]) == ([5.6, 6.0, 6.0], [5.6, 5.6, 6.0])
    assert (d245["verdict"], d245["verdict_alternative"]) == ("wrong", "wrong")
    assert st["wrong_rubric_dependent"] == "1/3" and st["rubric_dependent_ids"] == ["D7-58"]


def test_extraction_recall_two_ways_by_basis():
    from src.evaluation.claim_check import extraction_recall
    base = {"author": "ALLOCATOR", "relation": "eq", "allocation": {"in_effect": 1}}
    a = [{**base, "id": "a1", "day": 3, "quantity": {"name": "overflow"}, "value": "2", "basis": "copied"},
         {**base, "id": "a2", "day": 3, "quantity": {"name": "empty_beds"}, "value": "1", "basis": "derived"},
         {**base, "id": "a3", "day": 4, "quantity": {"name": "beds"}, "value": "9", "basis": "copied"}]
    b = [{**base, "id": "b1", "day": 3, "field": "reasons", "quantity": {"name": "overflow"}, "value": 2,
          "basis": "copied"},
         {**base, "id": "b2", "day": 3, "quantity": {"name": "empty_beds"}, "value": "2", "basis": "derived"}]
    r = extraction_recall(a, b, days={3})
    assert r["a_found_by_b"] == {"copied": "1/1", "derived": "0/1", "missed": ["a2"]}
    assert r["b_found_by_a"] == {"copied": "1/1", "derived": "0/1", "missed": ["b2"]}


def test_in_range_and_in_effect_allocation_on_a_shock_day(tmp_path):
    """R1 day 8 (nurse pool 37 -> 33): the in-effect allocation fails conservation, yet its beds and nurses
    are statements of the allocation itself and are compared; `in_range` is inclusive (rubric item 2)."""
    import json
    from pathlib import Path
    cur = {"in_effect": 7}
    base = {"author": "ALLOCATOR", "finding": "t", "day": 8, "allocation": cur}
    claims = [
        {**base, "id": "beds", "quantity": {"name": "beds", "departments": ["cardiology"]}, "relation": "eq",
         "value": 19},
        {**base, "id": "nurses", "quantity": {"name": "nurses"}, "relation": "eq", "value": 37},
        {**base, "id": "in", "quantity": {"name": "beds", "departments": ["cardiology"]},
         "relation": "in_range", "value": [17, 19]},
        {**base, "id": "out", "quantity": {"name": "beds", "departments": ["cardiology"]},
         "relation": "in_range", "value": [20, 22]},
    ]
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"claims": claims}), encoding="utf-8")
    v = {c["id"]: c["verdict"] for c in score("R1", spec, Path("results"))["claims"]}
    assert v == {"beds": "correct", "nurses": "correct", "in": "correct", "out": "wrong"}
