"""The owner's extraction of R1 days 3, 8, 18 (EVALUATION_PLAN.md §4 item 7a): conversion and comparison."""

from __future__ import annotations

import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from src.evaluation.owner_claims import compare, convert

FOLDER = Path("results/evaluations/R1/owner_extraction")


def test_owner_file_is_the_frozen_one_and_converts_deterministically():
    raw = (FOLDER / "owner_claims_d03_d08_d18.csv").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "6c7af169bc7f38d4de43fcb1ed86e5dc256f9d4121fc5902bbeab640fd283c47"
    a, na = convert(FOLDER)
    b, nb = convert(FOLDER)
    assert a == b and na == nb
    assert len(a) == 108 and len(na) == 18
    assert sum(c["quantity"] is None for c in a) == 5          # 2 vague, 3 unmapped


def test_comparison_two_ways_by_basis():
    owner, _ = convert(FOLDER)
    spec = json.loads(Path("results/evaluations/R1/explanation_claims_spec.json").read_text(encoding="utf-8"))
    raw = list(csv.DictReader(open(FOLDER / "owner_claims_d03_d08_d18.csv", encoding="utf-8-sig")))
    out = compare(owner, spec["claims"], {3, 8, 18}, raw)
    r = out["recall"]
    assert {k: v for k, v in r["a_found_by_b"].items() if k != "missed"} == \
        {"copied": "58/60", "derived": "28/47", "unclassified": "0/1"}
    assert {k: v for k, v in r["b_found_by_a"].items() if k != "missed"} == {"copied": "56/57", "derived": "29/49"}
    assert out["basis_agreement"]["agree"] == "72/86"
    assert len(out["out_of_universe_owner_rows"]) == 62
    assert all(o["assistant_also_left_out"] for o in out["out_of_universe_owner_rows"])
    assert len(out["adjudication"]) == 22 + 21


def test_decisions_a_b_move_no_claim_and_wrong_claim_tiers():
    """§11 #61 A-B change no claim's universe membership in R1 (all stated multi-tier needs are unrounded);
    the 75 wrong claims split 54 / 1 / 20 by the spare-free tier."""
    from src.evaluation.claim_review import tier
    from src.evaluation.decisions_ab import _out_of_universe
    assert _out_of_universe({"quantity": {"name": "need"}, "value": 6}, Fraction(56, 10)) == "B"
    assert _out_of_universe({"quantity": {"name": "need"}, "value": 5.6}, Fraction(56, 10)) is None
    assert _out_of_universe({"quantity": {"name": "need"}, "value": 5}, Fraction(5)) is None
    out = json.loads(Path("results/evaluations/R1/owner_extraction/comparison_7a_decisions_AB.json")
                     .read_text(encoding="utf-8"))
    assert out["difference"]["claim_ids"] == {"assistant": [], "owner": []}
    assert out["recall"]["as_frozen"] == out["recall"]["after_A_B"]
    claims = json.loads(Path("results/evaluations/R1/explanation_claims.json").read_text(encoding="utf-8"))["claims"]
    from collections import Counter
    assert Counter(tier(c) for c in claims if c["verdict"] == "wrong") == \
        {"wrong_only_primary": 54, "wrong_both_readings": 1, "no_spare_free_term": 20}


def test_owner_verdicts_cover_the_18_mappings_and_row_71_rule():
    """Owner verdicts (2026-11-19): the table covers exactly the non-mechanical mappings; row 71 is out of
    universe by the item-2 rule ((a) requirement - pool = 3 on day 8; (b) in-effect shortage 0.9)."""
    from src.evaluation.owner_verdicts import load_verdicts
    _, nonmech = convert(FOLDER)
    v = load_verdicts(FOLDER)
    assert set(v) == {n["row"] for n in nonmech}
    assert [r for r, x in v.items() if x["universe"] == "out"] == [71]
    out = json.loads((FOLDER / "comparison_7a_owner_verdicts.json").read_text(encoding="utf-8"))
    chk = out["item2_check"]["71"]
    assert (chk["a_requirement_minus_pool"], chk["b_shortage_in_effect"], chk["outcome"]) == (3, 0.9, "out")
    a = out["recall"]["after_owner_verdicts"]
    assert (a["a_found_by_b"]["derived"], a["b_found_by_a"]["derived"]) == ("28/46", "29/49")
    adj = list(csv.DictReader(open(FOLDER / "adjudication_7a.csv", encoding="utf-8-sig")))
    set_ = {(r["side"], r["owner_row"], r["cause"]) for r in adj if r["cause"]}
    assert set_ == {("owner_only", "64", "rubric_ambiguity"), ("owner_only", "71", "owner_encoding"),
                    ("owner_only", "166", "rubric_ambiguity")}


def test_item2_rule_on_r1_day_8():
    from src.evaluation.audit import load_records
    from src.evaluation.dataset import ROOT, load_dataset
    from src.evaluation.owner_verdicts import item2_check
    alloc = ROOT / "results" / "allocations" / "R1"
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    assert item2_check(ds, rec, 8, "3")["outcome"] == "out"
    assert item2_check(ds, rec, 8, "0.9")["outcome"] == "in"
    assert item2_check(ds, rec, 8, "5")["outcome"] == "stop"
