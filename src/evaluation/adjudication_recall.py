"""Item-7a recall after the owner's adjudication (owner, 2026-11-19; §11 #64-#65). Frozen files and earlier
comparison files are not modified.

    uv run python -m src.evaluation.adjudication_recall R1

Owner input tables read (never written):
  owner_verdicts_nonmech.csv      row 71 out of universe (owner_verdicts.py)
  owner_universe_overrides.csv    `out_of_universe` (re-checked from the data by the item-2 rule of row 71) and
                                  `duplicate` (the claim repeats an original's figure in another field: it leaves
                                  the denominator, the original stays; checked: same day, same departments, same
                                  stated value, original present)
  owner_adjudication_causes.csv   causes, for the descriptive figure and the counts

Primary recall: the pre-registered matching (`owner_claims.compare`), at three stages: as frozen; after the
earlier verdicts (row 71); after the overrides. Descriptive recall after adjudication (never instead of the
primary): an unmatched claim also counts as found if its cause is owner_encoding, assistant_encoding,
rubric_ambiguity or matching_rule and it has a counterpart in the display pairing (adjudication_view.pair).
Writes `<eval>/owner_extraction/comparison_7a_adjudicated.json`.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from .adjudication_view import pair
from .audit import load_records
from .claim_check import claim_key
from .dataset import ROOT, load_dataset
from .owner_claims import FILE, _canon, compare, convert
from .owner_inputs import ADJ_COLS, ADJ_FILE, ADJ_KEY, OwnerInputError, read_table
from .owner_verdicts import item2_check, load_verdicts

OVERRIDES_FILE = "owner_universe_overrides.csv"
OVERRIDE_COLS = ["claim_id", "action", "original", "comment", "set_by"]
FOUND_IF_PAIRED = ("owner_encoding", "assistant_encoding", "rubric_ambiguity", "matching_rule")


def _strip(r: dict) -> dict:
    return {k: {b: v for b, v in s.items() if b != "missed"} for k, s in r.items()}


def check_overrides(ds, rec, owner: list[dict], table: dict) -> dict:
    by_id = {c["id"]: c for c in owner}
    out = {}
    for (cid,), r in table.items():
        c = by_id.get(cid)
        if c is None:
            raise OwnerInputError(f"{OVERRIDES_FILE}: unknown claim {cid}")
        if r["action"] == "out_of_universe":
            chk = item2_check(ds, rec, c["day"], c["owner_raw"]["Value"].strip())
            if chk["outcome"] != "out":
                raise OwnerInputError(f"{OVERRIDES_FILE}: {cid}: item-2 rule gives {chk['outcome']!r}: {chk}")
            out[cid] = {"action": "out_of_universe", "requirement": chk["requirement"],
                        "pool_nurses": chk["pool_nurses"], "a_requirement_minus_pool": float(chk["a_requirement_minus_pool"]),
                        "b_shortage_in_effect": chk["b_shortage_in_effect"], "stated": chk["stated"]}
        elif r["action"] == "duplicate":
            o = by_id.get(r["original"])
            if o is None:
                raise OwnerInputError(f"{OVERRIDES_FILE}: {cid}: unknown original {r['original']!r}")
            same = (o["day"] == c["day"], (o["quantity"] or {}).get("departments") == (c["quantity"] or {}).get("departments"),
                    str(o["value"]) == str(c["value"]))
            if not all(same):
                raise OwnerInputError(f"{OVERRIDES_FILE}: {cid} vs {o['id']}: day / departments / value differ {same}")
            out[cid] = {"action": "duplicate", "original": o["id"], "day": c["day"], "value": c["value"]}
        else:
            raise OwnerInputError(f"{OVERRIDES_FILE}: {cid}: action {r['action']!r} not in ['out_of_universe', 'duplicate']")
    return out


def main(run_id: str, eval_dir: Path | None = None, alloc_dir: Path | None = None) -> dict:
    ev = eval_dir or ROOT / "results" / "evaluations" / run_id
    alloc = alloc_dir or ROOT / "results" / "allocations" / run_id
    folder = ev / "owner_extraction"
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    owner, _ = convert(folder)
    spec = json.loads((ev / "explanation_claims_spec.json").read_text(encoding="utf-8"))["claims"]
    raw = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))
    days = {c["day"] for c in owner}
    verdict_out = {f"OWN-D{c['day']:02d}-r{c['owner_row']:03d}" for c in owner
                   if load_verdicts(folder).get(c["owner_row"], {}).get("universe") == "out"}
    overrides = check_overrides(ds, rec, owner, read_table(folder / OVERRIDES_FILE, OVERRIDE_COLS, ("claim_id",)))
    out2 = verdict_out | {i for i, o in overrides.items() if o["action"] == "out_of_universe"}
    dup = {i for i, o in overrides.items() if o["action"] == "duplicate"}

    def recall(drop: set[str]) -> dict:
        return compare([dict(c) for c in owner if c["id"] not in drop], [dict(c) for c in spec], days, raw)

    frozen, earlier, after = recall(set()), recall(verdict_out), recall(out2 | dup)

    # descriptive: unmatched claims with an encoding-type cause and a display-pairing counterpart count as found
    causes = {k: r["cause"].strip() for k, r in read_table(folder / ADJ_FILE, ADJ_COLS, ADJ_KEY).items()}
    o_c = [dict(c) for c in owner if c["id"] not in out2 | dup]
    m_c = [dict(c) for c in spec]
    compare(o_c, m_c, days, raw)                                 # sets day_ref
    mine = [c for c in m_c if c["author"] == "ALLOCATOR" and c.get("day_ref") in days]
    km, ko = {claim_key(_canon(c)) for c in mine}, {claim_key(_canon(c)) for c in o_c}
    oo = [c for c in o_c if claim_key(_canon(c)) not in km]
    ao = [c for c in mine if claim_key(_canon(c)) not in ko]
    paired = {x["id"] for p in pair(oo, ao) if p[0] and p[1] for x in p[:2]}
    found = {"owner_only": {c["id"] for c in oo if causes.get(("owner_only", c["id"])) in FOUND_IF_PAIRED
                            and c["id"] in paired},
             "assistant_only": {c["id"] for c in ao if causes.get(("assistant_only", c["id"])) in FOUND_IF_PAIRED
                                and c["id"] in paired}}

    def descriptive(ref, other_keys, extra):
        res = {}
        for c in ref:
            e = res.setdefault(c.get("basis") or "unclassified", [0, 0])
            e[0] += claim_key(_canon(c)) in other_keys or c["id"] in extra
            e[1] += 1
        return {k: f"{v[0]}/{v[1]}" for k, v in sorted(res.items())}

    desc = {"a_found_by_b": descriptive(o_c, km, found["owner_only"]),
            "b_found_by_a": descriptive(mine, ko, found["assistant_only"])}
    by_side = {s: Counter(v or "(empty)" for (side, _), v in causes.items() if side == s)
               for s in ("owner_only", "assistant_only")}
    res = {
        "a_is": "owner's claims (a_found_by_b: found by the assistant)", "b_is": "assistant's claims",
        "primary_recall": {"as_frozen": _strip(frozen["recall"]),
                           "after_earlier_verdicts_row_71": _strip(earlier["recall"]),
                           "after_adjudication_overrides": _strip(after["recall"])},
        "primary_missed_after_overrides": {k: v["missed"] for k, v in after["recall"].items()},
        "descriptive_recall_after_adjudication": {
            "label": "DESCRIPTIVE ONLY, reported next to the primary figure, never instead of it",
            "rule": "unmatched claim found if cause in " + ", ".join(FOUND_IF_PAIRED) +
                    " and it has a counterpart in the display pairing (adjudication_view.pair)",
            "recall": desc, "counted_found": {k: sorted(v) for k, v in found.items()}},
        "universe_and_duplicates": {"out_of_universe": sorted(out2), "duplicates_left_out": sorted(dup),
                                    "override_checks": overrides},
        "causes_by_side": {s: dict(sorted(c.items())) for s, c in by_side.items()},
        "causes_total": dict(sorted((by_side["owner_only"] + by_side["assistant_only"]).items())),
        "not_applied_note": "owner rows 54 and 57 (same claim key, both matched) are counted separately, as frozen",
        "variant_not_applied_row_57_also_duplicate": {
            "label": "NOT APPLIED: shown for the owner's decision (rows 54 and 57 were never collapsed)",
            "recall": _strip(recall(out2 | dup | {"OWN-D03-r057"})["recall"])},
    }
    (folder / "comparison_7a_adjudicated.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n",
                                                           encoding="utf-8", newline="\n")
    return res


if __name__ == "__main__":
    r = main(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("primary_recall", "causes_by_side")}, indent=2))
    print(json.dumps(r["descriptive_recall_after_adjudication"]["recall"]))
