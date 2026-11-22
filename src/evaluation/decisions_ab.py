"""Owner decisions §11 #61 A-B (2026-11-18, taken after the item-7a comparison had been seen): recall and claim
accuracy as frozen and after the decisions, side by side. The frozen files are not modified.

    uv run python -m src.evaluation.decisions_ab R1

A: patient attributes are outside the universe (item 1); a named patient in or out of a bed stays in.
   Out-of-universe quantities: `patient` (attribute match), `mean_arrivals`, `census`, `requirement`.
B: a nurse figure stating the rounded requirement over several tiers, ceil(sum of need), is outside the
   universe; the unrounded summed need is in. Applied to `need` claims: out if the stated value is written as
   an integer, equals the ceiling of the computed need, and the computed need is not an integer.
Writes `<eval>/owner_extraction/comparison_7a_decisions_AB.json` and
`<eval>/owner_review/multitier_nurse_claims.csv`.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from .audit import load_records
from .claim_check import VERDICTS, quantity, score_claim
from .dataset import ROOT, load_dataset
from .owner_claims import FILE, compare, convert, encoding
from src.utils.paths import long_path

OUT_A = {"patient", "mean_arrivals", "census", "requirement"}


def _out_of_universe(c: dict, need_value) -> str | None:
    q = c.get("quantity")
    if q is None:
        return None
    if q["name"] in OUT_A:
        return "A"
    if q["name"] == "need" and need_value is not None and c.get("value") is not None:
        s = str(c["value"])
        if "." not in s and Fraction(s) == math.ceil(need_value) and Fraction(need_value).denominator != 1:
            return "B"
    return None


def _accuracy(claims: list[dict]) -> dict:
    by_cat = defaultdict(lambda: {v: 0 for v in VERDICTS})
    for c in claims:
        by_cat[c.get("category")][c["verdict"]] += 1
    total = {v: sum(1 for c in claims if c["verdict"] == v) for v in VERDICTS}
    return {"total": total, "by_category": dict(sorted(by_cat.items()))}


def main(run_id: str) -> None:
    ev = long_path(ROOT / "results" / "evaluations" / run_id)        # Log #117
    alloc = long_path(ROOT / "results" / "allocations" / run_id)
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    scored = [c for c in json.loads((ev / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR"]
    spec = json.loads((ev / "explanation_claims_spec.json").read_text(encoding="utf-8"))["claims"]
    folder = ev / "owner_extraction"
    owner, _ = convert(folder)
    raw = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))

    def need_of(c):
        q = c.get("quantity")
        return quantity(ds, rec, c["day"], None, q) if q and q["name"] == "need" else None

    moved_a = {c["id"]: _out_of_universe(c, need_of(c)) for c in scored}
    moved_o = {c["id"]: _out_of_universe(c, need_of(c)) for c in owner}
    moved = {"assistant": sorted(i for i, r in moved_a.items() if r),
             "owner": sorted(i for i, r in moved_o.items() if r)}
    days = {c["day"] for c in owner}
    frozen = compare([dict(c) for c in owner], [dict(c) for c in spec], days, raw)
    after = compare([dict(c) for c in owner if not moved_o[c["id"]]],
                    [dict(c) for c in spec if not moved_a.get(c["id"])], days, raw)
    owner_scored = [score_claim(ds, rec, c) for c in owner]
    out = {
        "decisions": "PROJECT_SPEC.md §11 #61 A-B, taken after the item-7a comparison had been seen",
        "moved_out_of_universe": {"assistant": {i: moved_a[i] for i in moved["assistant"]},
                                  "owner": {i: moved_o[i] for i in moved["owner"]}},
        "recall": {"as_frozen": frozen["recall"], "after_A_B": after["recall"]},
        "accuracy_assistant_full_R1": {"as_frozen": _accuracy(scored),
                                       "after_A_B": _accuracy([c for c in scored if not moved_a[c["id"]]])},
        "accuracy_owner_days_3_8_18": {"as_frozen": _accuracy(owner_scored),
                                       "after_A_B": _accuracy([c for c in owner_scored if not moved_o[c["id"]]])},
    }
    out["difference"] = {
        "claim_ids": moved,
        "recall_changed": out["recall"]["as_frozen"] != out["recall"]["after_A_B"],
        "accuracy_changed": (out["accuracy_assistant_full_R1"]["as_frozen"]
                             != out["accuracy_assistant_full_R1"]["after_A_B"]
                             or out["accuracy_owner_days_3_8_18"]["as_frozen"]
                             != out["accuracy_owner_days_3_8_18"]["after_A_B"])}
    rows = []
    for c in owner:
        if c["owner_row"] in (115, 116, 117, 118):
            v = need_of(c)
            rows.append({"row": c["owner_row"], "department": c["quantity"]["departments"][0], "stated": c["value"],
                         "unrounded_need_L2_L3": float(v), "ceiling": math.ceil(v),
                         "decision_B": "out (rounded requirement)" if moved_o[c["id"]] else "in universe (unrounded sum)"})
    out["owner_rows_115_118"] = rows
    (folder / "comparison_7a_decisions_AB.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8",
                                                           newline="\n")
    wrong = {c["id"] for c in scored if c["verdict"] == "wrong"}
    n = 0
    with open(ev / "owner_review" / "multitier_nurse_claims.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "day", "text", "encoding", "stated", "computed_unrounded", "ceiling_of_computed",
                    "verdict", "among_75_wrong", "decision_B"])
        for c in scored:
            q = c.get("quantity")
            if not q or q["name"] not in ("need", "covered_need", "shortage") or len(q.get("levels", [1, 2, 3])) < 2:
                continue
            comp = c["computed"]
            ceil = "" if comp is None or isinstance(comp, list) else math.ceil(Fraction(str(comp)))
            w.writerow([c["id"], c["day"], c["text"], encoding(c), c.get("value"), json.dumps(comp), ceil,
                        c["verdict"], c["id"] in wrong,
                        "out (rounded requirement)" if moved_a[c["id"]] == "B" else
                        ("in (unrounded need)" if q["name"] == "need" else "n/a (coverage or shortage figure)")])
            n += 1
    print(json.dumps({"moved": moved, "recall_changed": out["difference"]["recall_changed"],
                      "accuracy_changed": out["difference"]["accuracy_changed"], "rows_115_118": rows,
                      "multitier_claims_listed": n}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
