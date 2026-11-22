"""Display file for the owner's review of the unverifiable claims (owner, 2026-11-19). DISPLAY ONLY: not an
input (verdicts go in `owner_review_unverifiable.csv`), changes no verdict and no encoding.

    uv run python -m src.evaluation.unverifiable_view R1

Per claim: day, field, full sentence, the reason (from the extraction note: "alternative fails validation",
"vague qualifier", "ambiguous referent", else "other"), and, where a value can be computed, the value under the
most natural reading. The readings are fixed below (READINGS), one per claim id, stated in words next to the
value; they are the assistant's, for display, and are not scored. Writes
`<eval>/owner_review/unverifiable_26_check.csv`.
"""

from __future__ import annotations

import csv
import json
import sys
from fractions import Fraction
from pathlib import Path

from src.environment.whatif import simulate
from src.utils.constants import DEPARTMENTS

from .audit import load_records
from .claim_check import day_context, quantity, resolve_allocation
from .dataset import ROOT, load_dataset
from .rubric_check_view import sentence
from src.utils.paths import long_path

AB = {"cardiology": "CA", "internal_medicine": "IM", "neurology": "NE", "orthopedics": "OR"}   # by name (R54)
assert set(AB) == set(DEPARTMENTS)
BANNER = ("# GENERATED DISPLAY FILE (src/evaluation/unverifiable_view.py): unverifiable claims; not an input; "
          "verdicts go in owner_review_unverifiable.csv")


def _alloc(beds, nurses):
    order = ("cardiology", "internal_medicine", "neurology", "orthopedics")
    return {"beds": dict(zip(order, beds)), "nurses": dict(zip(order, nurses))}


def reason(note: str) -> str:
    n = note.lower()
    if "fails validation" in n:
        return "alternative fails validation" + ("; also vague qualifier" if "vague qualifier" in n else "")
    if "vague qualifier" in n:
        return "vague qualifier"
    if "ambiguous referent" in n or "ambiguous quantifier" in n:
        return "ambiguous referent"
    return "other"


def readings(ds, rec) -> dict[str, tuple[str, str]]:
    """id -> (reading in words, value)."""
    def q(day, alloc, name, deps=None, levels=None):
        spec = {"name": name}
        if deps:
            spec["departments"] = deps
        if levels:
            spec["levels"] = levels
        v = quantity(ds, rec, day, alloc, spec)
        return None if v is None else (float(v) if isinstance(v, Fraction) else v)

    def per(day, alloc, name, levels):
        return ", ".join(f"{AB[d]} {q(day, alloc, name, [d], levels)}" for d in DEPARTMENTS)

    def bed_minimums(day):
        return {AB[d]: q(day, None, "holders", [d]) + q(day, None, "queue", [d], [2, 3]) for d in DEPARTMENTS}

    def min_l2_shortage(day, alloc):
        ctx = day_context(ds, rec, day)
        beds, _ = resolve_allocation(rec, alloc)
        pool, best = ds.pool_nurses[day], None
        for a in range(pool + 1):
            for b in range(pool + 1 - a):
                for c in range(pool + 1 - a - b):
                    n = dict(zip(DEPARTMENTS, (a, b, c, pool - a - b - c)))
                    s = simulate(beds, n, ctx)
                    v = sum(Fraction(s.shortage[d][2]) for d in DEPARTMENTS)
                    best = v if best is None or v < best else best
        return float(best)

    def l1_arrived(day, arrival, alloc):
        ctx = day_context(ds, rec, day)
        beds, nurses = resolve_allocation(rec, alloc)
        r = simulate(beds, nurses, ctx)
        g = [p for p in ctx.present if p.complexity == 1 and p.arrival_day == arrival]
        return f"{sum(p.patient_id in r.assignment.in_bed for p in g)} of {len(g)} in a bed"

    e7, e12, e14, e20, d26, d27, d30 = ({"in_effect": 7}, {"in_effect": 12}, {"in_effect": 14}, {"in_effect": 20},
                                        {"decided": 26}, {"decided": 27}, {"decided": 30})
    b22, n22 = resolve_allocation(rec, {"in_effect": 22})
    b23 = {"beds": {**b22, "orthopedics": 7}, "nurses": n22}  # "previous beds with orthopedics cut to 7, nurses unchanged"
    a10 = _alloc((15, 35, 14, 32), (5, 12, 7, 9))
    a16 = _alloc((34, 30, 16, 20), (14, 10, 8, 5))
    a18 = _alloc((37, 29, 20, 14), (14, 9, 10, 4))
    b19 = _alloc((35, 33, 19, 13), (14, 10, 9, 4))
    b20 = _alloc((30, 37, 19, 14), (12, 13, 10, 2))
    a28 = _alloc((30, 33, 15, 18), (14, 11, 6, 6))
    mins = bed_minimums(30)
    out = {
        "R1-D08-22": ("overflow under A (day-7 allocation) on day 8", q(8, e7, "overflow")),
        "R1-D08-23": ("NE empty beds under A", q(8, e7, "empty_beds", ["neurology"])),
        "R1-D08-24": ("OR empty beds under A", q(8, e7, "empty_beds", ["orthopedics"])),
        "R1-D10-33": ("L1 need covered per department under A (NE L2 shortage "
                      f"{q(10, a10, 'shortage', ['neurology'], [2])})", per(10, a10, "covered_need", [1])),
        "R1-D13-25": ("OR, IM empty beds under A (in effect, day 12)",
                      f"{q(13, e12, 'empty_beds', ['orthopedics'])}, {q(13, e12, 'empty_beds', ['internal_medicine'])}"),
        "R1-D15-29": ("OR, IM empty beds under A (in effect, day 14)",
                      f"{q(15, e14, 'empty_beds', ['orthopedics'])}, {q(15, e14, 'empty_beds', ['internal_medicine'])}"),
        "R1-D16-29": ("L1 need covered per department under A (NE L2 shortage "
                      f"{q(16, a16, 'shortage', ['neurology'], [2])})", per(16, a16, "covered_need", [1])),
        "R1-D18-19": ("L1 need covered / L1 need per department under A",
                      "; ".join(f"{AB[d]} {q(18, a18, 'covered_need', [d], [1])}/{q(18, None, 'need', [d], [1])}"
                                for d in DEPARTMENTS)),
        "R1-D19-19": ("L1 need covered per department under B (NE L2 shortage "
                      f"{q(19, b19, 'shortage', ['neurology'], [2])})", per(19, b19, "covered_need", [1])),
        "R1-D19-23": ("minimum L2 shortage over every integer split of the nurse pool (beds as decided)",
                      min_l2_shortage(19, {"decided": 19})),
        "R1-D20-39": ("L1 need covered per department under B (OR L2 shortage "
                      f"{q(20, b20, 'shortage', ['orthopedics'], [2])})", per(20, b20, "covered_need", [1])),
        "R1-D21-10": ("IM overflow under the previous (day-20) allocation", q(21, e20, "overflow", ["internal_medicine"])),
        "R1-D21-11": ("CA spare / empty beds under the previous allocation",
                      f"{q(21, e20, 'spare_beds', ['cardiology'])} / {q(21, e20, 'empty_beds', ['cardiology'])}"),
        "R1-D21-12": ("NE spare / empty beds under the previous allocation",
                      f"{q(21, e20, 'spare_beds', ['neurology'])} / {q(21, e20, 'empty_beds', ['neurology'])}"),
        "R1-D23-17": ("OR overflow under B (day-22 beds, orthopedics 7)", q(23, b23, "overflow", ["orthopedics"])),
        "R1-D23-18": ("OR L2 overflow under B", q(23, b23, "overflow", ["orthopedics"], [2])),
        "R1-D23-19": ("L1 shortage under B", q(23, b23, "shortage", None, [1])),
        "R1-D26-36": ("L1 patients who arrived day 25, under the decided allocation", l1_arrived(26, 25, d26)),
        "R1-D27-53": ("L1 need covered / L1 need, decided allocation",
                      f"{q(27, d27, 'covered_need', None, [1])} / {q(27, None, 'need', None, [1])}"),
        "R1-D28-17": ("OR L1 need covered / need under A",
                      f"{q(28, a28, 'covered_need', ['orthopedics'], [1])} / {q(28, None, 'need', ['orthopedics'], [1])}"),
        "R1-D30-47": ("CA occupied + queued L2-3", mins["CA"]),
        "R1-D30-48": ("IM occupied + queued L2-3", mins["IM"]),
        "R1-D30-49": ("NE occupied + queued L2-3", mins["NE"]),
        "R1-D30-50": ("OR occupied + queued L2-3", mins["OR"]),
        "R1-D30-51": ("sum of the four minimums", sum(mins.values())),
        "R1-D30-52": ("bed pool minus the sum of the minimums (decided: spare "
                      f"{q(30, d30, 'spare_beds')}, empty {q(30, d30, 'empty_beds')})", ds.pool_beds[30] - sum(mins.values())),
    }
    return {k: (w, "" if v is None else str(v)) for k, (w, v) in out.items()}


def main(run_id: str, eval_dir: Path | None = None, alloc_dir: Path | None = None) -> list[dict]:
    ev = long_path(eval_dir or ROOT / "results" / "evaluations" / run_id)        # Log #117
    alloc = long_path(alloc_dir or ROOT / "results" / "allocations" / run_id)
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    hist = {}
    for line in open(alloc / "decision_history.jsonl", encoding="utf-8"):
        h = json.loads(line)
        hist[h["day"]] = h["explanation"]
    claims = [c for c in json.loads((ev / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR" and c["verdict"] == "unverifiable"]
    vals = readings(ds, rec)
    missing = sorted({c["id"] for c in claims} - set(vals))
    if missing:
        raise SystemExit(f"no reading defined for {missing}")
    rows = []
    for c in claims:
        day = int(c["id"].split("-D")[1][:2])
        found = sentence(hist[day].get(c["field"], ""), c["text"])
        rows.append({"id": c["id"], "day": day, "field": c["field"], "text": c["text"],
                     "full_sentence": found[0] if found else hist[day].get(c["field"], ""),
                     "reason": reason(c.get("note", "")), "reading": vals[c["id"]][0], "value": vals[c["id"]][1],
                     "note": c.get("note", "")})
    with open(ev / "owner_review" / "unverifiable_26_check.csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(BANNER + "\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    r = main(sys.argv[1])
    from collections import Counter
    print(len(r), "rows", dict(Counter(x["reason"] for x in r)))
