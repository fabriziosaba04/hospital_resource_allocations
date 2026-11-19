"""Owner verdicts on the 18 non-mechanical mappings of item 7a (owner, 2026-11-19). The frozen files are not
modified (`owner_claims_d03_d08_d18.csv`, `explanation_claims_spec.json`), nor are the earlier comparison files.

    uv run python -m src.evaluation.owner_verdicts R1

Input: `<eval>/owner_extraction/owner_verdicts_nonmech.csv` (one row per non-mechanical mapping: verdict,
comment, universe in/out, adjudication cause, who set it). Row 71 follows the owner's rule of item 2: out of
universe if the hospital N1 requirement minus the nurse pool on its day equals the stated value; in universe
(allocation in effect) if the total shortage under the in-effect allocation does; otherwise stop. The rule is
re-checked here from the data, never read off the table.

Writes:
  non_mechanical_mappings.csv   the converter's 18 rows plus `owner_verdict`, `owner_comment`
  adjudication_7a.csv           `cause` filled for the owner-only rows of the verdict table that carry a cause,
                                with a new column `cause_set_by`; every other row unchanged
  comparison_7a_owner_verdicts.json   recall before / after the owner rows marked out of universe are dropped
"""

from __future__ import annotations

import csv
import json
import sys
from fractions import Fraction
from pathlib import Path

from src.utils.constants import DEPARTMENTS

from .audit import load_records
from .claim_check import quantity
from .dataset import ROOT, load_dataset
from .owner_claims import FILE, compare, convert

VERDICTS_FILE = "owner_verdicts_nonmech.csv"


def load_verdicts(folder: Path) -> dict[int, dict]:
    return {int(r["row"]): r for r in csv.DictReader(open(folder / VERDICTS_FILE, encoding="utf-8"))}


def item2_check(ds, rec, day: int, stated) -> dict:
    """(a) hospital N1 requirement (sum of department ceilings) minus the nurse pool, in nurses;
    (b) total shortage in need units under the allocation in effect (end of day-1)."""
    req = sum(quantity(ds, rec, day, None, {"name": "requirement", "departments": [d]}) for d in DEPARTMENTS)
    pool = quantity(ds, rec, day, None, {"name": "pool_nurses"})
    a = req - pool
    b = quantity(ds, rec, day, {"in_effect": day - 1}, {"name": "shortage"})
    s = Fraction(str(stated))
    hit_a, hit_b = a == s, b is not None and b == s
    outcome = "out" if hit_a and not hit_b else "in" if hit_b and not hit_a else "stop"
    return {"requirement": req, "pool_nurses": pool, "a_requirement_minus_pool": a,
            "b_shortage_in_effect": None if b is None else float(b), "stated": stated, "outcome": outcome}


def _strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if k != "missed"}


def main(run_id: str) -> None:
    ev = ROOT / "results" / "evaluations" / run_id
    alloc = ROOT / "results" / "allocations" / run_id
    folder = ev / "owner_extraction"
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    verdicts = load_verdicts(folder)
    owner, nonmech = convert(folder)
    assert {n["row"] for n in nonmech} == set(verdicts), "verdict table must cover exactly the 18 mappings"

    # item 2 for every row the table moves out of universe: the rule must hold on the data
    by_row = {c["owner_row"]: c for c in owner}
    checks = {}
    for row, v in verdicts.items():
        if v["universe"] == "out":
            c = by_row[row]
            chk = item2_check(ds, rec, c["day"], c["owner_raw"]["Value"].strip())
            if chk["outcome"] != "out":
                raise SystemExit(f"row {row}: item-2 rule gives {chk['outcome']!r}, not 'out': {chk}")
            checks[row] = {k: (float(x) if isinstance(x, Fraction) else x) for k, x in chk.items()}

    # 1. verdict columns on non_mechanical_mappings.csv
    fields = ["row", "day", "field", "text", "owner_quantity", "owner_allocation", "mapped_to", "reason",
              "owner_verdict", "owner_comment"]
    with open(folder / "non_mechanical_mappings.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for n in nonmech:
            v = verdicts[n["row"]]
            w.writerow({**n, "owner_verdict": v["owner_verdict"], "owner_comment": v["owner_comment"]})

    # 2. causes on adjudication_7a.csv (owner-only rows of the verdict table that carry a cause)
    path = folder / "adjudication_7a.csv"
    adj = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    filled = []
    for a in adj:
        a.setdefault("cause_set_by", "")
        a["cause_set_by"] = a.get("cause_set_by") or ""
        if a["side"] == "owner_only" and a["owner_row"] and int(a["owner_row"]) in verdicts:
            v = verdicts[int(a["owner_row"])]
            if v["cause"]:
                a["cause"], a["cause_set_by"] = v["cause"], v["set_by"]
                filled.append(int(a["owner_row"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(adj[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(adj)

    # 3. recall before / after the owner rows moved out of universe
    spec = json.loads((ev / "explanation_claims_spec.json").read_text(encoding="utf-8"))["claims"]
    raw = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))
    out_rows = {r for r, v in verdicts.items() if v["universe"] == "out"}
    raw_after = [{**r, "Category": "out_of_universe"} if i in out_rows else r for i, r in enumerate(raw, 1)]
    days = {c["day"] for c in owner}
    before = compare([dict(c) for c in owner], [dict(c) for c in spec], days, raw)
    after = compare([dict(c) for c in owner if c["owner_row"] not in out_rows], [dict(c) for c in spec], days,
                    raw_after)
    amb = {r for r, v in verdicts.items() if v["owner_verdict"] == "rubric_ambiguity"}
    descr = compare([dict(c) for c in owner if c["owner_row"] not in out_rows | amb], [dict(c) for c in spec],
                    days, raw_after)
    res = {
        "decisions": "owner verdicts on the 18 non-mechanical mappings (2026-11-19); row 71 by the owner's item-2 rule",
        "moved_out_of_universe": sorted(out_rows),
        "item2_check": checks,
        "causes_filled_owner_rows": sorted(filled),
        "recall": {"before": before["recall"], "after_owner_verdicts": after["recall"]},
        "recall_if_null_quantities_collide": {"before": before["recall_if_null_quantities_collide"],
                                              "after_owner_verdicts": after["recall_if_null_quantities_collide"]},
        "out_of_universe_rows": {"before": len(before["out_of_universe_owner_rows"]),
                                 "after_owner_verdicts": len(after["out_of_universe_owner_rows"]),
                                 "moved_rows": [o for o in after["out_of_universe_owner_rows"]
                                                if o["row"] in out_rows]},
        "descriptive_only_rubric_ambiguity_rows_also_dropped": {
            "rows": sorted(amb), "applied": False,
            "note": "not a decision: rows 64 and 166 stay in the universe; shown for the owner's review",
            "recall": {k: _strip(v) for k, v in descr["recall"].items()}},
    }
    (folder / "comparison_7a_owner_verdicts.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n",
                                                             encoding="utf-8", newline="\n")
    print(json.dumps({"item2": checks, "filled": res["causes_filled_owner_rows"],
                      "before": {k: _strip(v) for k, v in before["recall"].items()},
                      "after": {k: _strip(v) for k, v in after["recall"].items()},
                      "descriptive": res["descriptive_only_rubric_ambiguity_rows_also_dropped"]["recall"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
