"""The owner's extraction of R1 days 3, 8, 18 (EVALUATION_PLAN.md §4 item 7a): conversion and comparison."""

from __future__ import annotations

import csv
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
