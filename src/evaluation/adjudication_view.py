"""Side-by-side view of the item-7a unmatched claims (owner, 2026-11-19). DISPLAY ONLY: a generated file, not an
input; it plays no part in matching, changes no matching rule and fills no cause.

    uv run python -m src.evaluation.adjudication_view R1

Reads the frozen extractions through `owner_claims.convert` / `compare` (the same unmatched rows as
`adjudication_7a.csv`), never `owner_adjudication_causes.csv`. Writes
`<eval>/owner_extraction/adjudication_pairs_view.csv` (first line: a GENERATED DISPLAY FILE banner) and
`adjudication_pairs_summary.json`.

Pairing rule (display only), between an owner-only and an assistant-only claim of the same explanation day:
  texts are normalised (lower case, hyphens to spaces, whitespace collapsed);
  P1 "contains"   one normalised text contains the other;
  P2 "number"     they share a number token together with an adjacent word on the same side of it (a common
                  bigram "word n" or "n word"), e.g. "reduced by 4" / "nurse pool reduced by 4 (37": "by 4".
Pairs are one-to-one: P1 candidates first, then P2 among the claims still unpaired; within a rule, the
candidate with the highest text similarity (difflib ratio), then the lower id. Claims left unpaired are
singles.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

from src.utils.constants import DEPARTMENTS

from .audit import load_records
from .claim_check import claim_key, score_claim
from .dataset import ROOT, load_dataset
from .owner_claims import ABBR, FILE, _alloc_str, _canon, compare, convert
from src.utils.paths import guard_write, long_path

BANNER = ("# GENERATED DISPLAY FILE (src/evaluation/adjudication_view.py): not an input, plays no part in matching; "
          "edit causes in owner_adjudication_causes.csv")
KEY_FIELDS = ("day", "quantity", "allocation", "compare_allocation", "relation", "value")


def _text(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower().replace("-", " ")).strip()


def _tokens(t: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?|[a-z]+", _text(t))


def _number_bigrams(t: str) -> set[tuple[str, str]]:
    tk = _tokens(t)
    out = set()
    for i, w in enumerate(tk):
        if re.fullmatch(r"\d+(?:\.\d+)?", w):
            if i > 0:
                out.add((tk[i - 1], w))
            if i + 1 < len(tk):
                out.add((w, tk[i + 1]))
    return out


def rule(a: str, b: str) -> tuple[str, str] | None:
    x, y = _text(a), _text(b)
    if x and y and (x in y or y in x):
        return "P1 contains", ""
    shared = _number_bigrams(a) & _number_bigrams(b)
    if shared:
        return "P2 number", "; ".join(" ".join(s) for s in sorted(shared))
    return None


def pair(owner_only: list[dict], assistant_only: list[dict]) -> list[tuple[dict | None, dict | None, str, str]]:
    cands = []
    for o in owner_only:
        for a in assistant_only:
            if o["day_ref"] != a["day_ref"]:
                continue
            r = rule(o["text"], a["text"])
            if r:
                sim = difflib.SequenceMatcher(None, _text(o["text"]), _text(a["text"])).ratio()
                cands.append((r[0][:2], -sim, o["id"], a["id"], r))
    cands.sort()
    used_o, used_a, pairs = set(), set(), []
    for _, _, oid, aid, r in cands:
        if oid in used_o or aid in used_a:
            continue
        used_o.add(oid)
        used_a.add(aid)
        pairs.append((oid, aid, r))
    by_o = {c["id"]: c for c in owner_only}
    by_a = {c["id"]: c for c in assistant_only}
    out = [(by_o[o], by_a[a], r[0], r[1]) for o, a, r in pairs]
    out += [(c, None, "", "") for c in owner_only if c["id"] not in used_o]
    out += [(None, c, "", "") for c in assistant_only if c["id"] not in used_a]
    kind = lambda p: 0 if p[0] and p[1] else (1 if p[0] else 2)
    return sorted(out, key=lambda p: ((p[0] or p[1])["day_ref"], kind(p), (p[0] or p[1])["id"]))


def _side(c: dict | None, scored: dict | None) -> dict:
    if c is None:
        return {k: "" for k in ("id", "text", "field", "day", "quantity", "departments", "levels", "allocation",
                                "compare_allocation", "relation", "value", "basis", "recomputed", "recomputed_compare",
                                "verdict")}
    q = c.get("quantity") or {}
    name = q.get("name", "")
    if "patient_id" in q:
        name += f"({q['patient_id']})"
    num = lambda v: "" if v is None else json.dumps(v)
    return {"id": c["id"], "text": c["text"], "field": c.get("field", ""), "day": c["day"],
            "quantity": name or "(null)",
            "departments": ",".join(ABBR[d] for d in q["departments"]) if "departments" in q else ("all" if q else ""),
            "levels": "".join(map(str, q["levels"])) if "levels" in q else ("all" if q else ""),
            "allocation": _alloc_str(c.get("allocation")),
            "compare_allocation": _alloc_str(c["compare_allocation"]) if c.get("compare_allocation") else "",
            "relation": c.get("relation") or "", "value": "" if c.get("value") is None else json.dumps(c["value"]),
            "basis": c.get("basis") or "", "recomputed": num(scored.get("computed")),
            "recomputed_compare": num(scored.get("computed_compare")), "verdict": scored["verdict"]}


def differing(o: dict, a: dict) -> list[str]:
    """Matching-key fields (claim_key; field ignored) that differ, after the comparison's own normalisation."""
    co, ca = _canon(o), _canon(a)
    out = []
    for f in KEY_FIELDS:
        vo, va = co.get(f), ca.get(f)
        if f == "value":
            vo, va = (None if vo is None else str(vo)), (None if va is None else str(va))
        if f == "quantity" and (vo or {}).get("name") == "__no_quantity__":
            vo = None
        if f == "quantity" and (va or {}).get("name") == "__no_quantity__":
            va = None
        if vo != va:
            out.append(f)
    return out


def quantity_parts(o: dict, a: dict) -> list[str]:
    qo, qa = o.get("quantity") or {}, a.get("quantity") or {}
    if not qo or not qa:
        return ["null on one side"]
    parts = []
    for k, default in (("name", None), ("departments", list(DEPARTMENTS)), ("levels", [1, 2, 3]),
                       ("patient_id", None)):
        vo, va = qo.get(k, default), qa.get(k, default)
        if k in ("departments", "levels") and vo is not None and va is not None:
            vo, va = sorted(vo, key=str), sorted(va, key=str)
        if vo != va:
            parts.append(k)
    return parts


def main(run_id: str, eval_dir: Path | None = None, alloc_dir: Path | None = None) -> dict:
    ev = long_path(eval_dir or ROOT / "results" / "evaluations" / run_id)        # Log #117
    alloc = long_path(alloc_dir or ROOT / "results" / "allocations" / run_id)
    folder = ev / "owner_extraction"
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    ds, rec = load_dataset(m["dataset_id"], Path(m["data_root"])), load_records(alloc)
    owner, _ = convert(folder)
    spec = json.loads((ev / "explanation_claims_spec.json").read_text(encoding="utf-8"))["claims"]
    raw = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))
    days = {c["day"] for c in owner}
    o_c, m_c = [dict(c) for c in owner], [dict(c) for c in spec]
    compare(o_c, m_c, days, raw)                          # sets day_ref; same selection as adjudication_7a.csv
    mine = [c for c in m_c if c["author"] == "ALLOCATOR" and c.get("day_ref") in days]
    keys_m = {claim_key(_canon(c)) for c in mine}
    keys_o = {claim_key(_canon(c)) for c in o_c}
    owner_only = [c for c in o_c if claim_key(_canon(c)) not in keys_m]
    assistant_only = [c for c in mine if claim_key(_canon(c)) not in keys_o]
    pairs = pair(owner_only, assistant_only)

    rows, freq, combos = [], Counter(), Counter()
    for o, a, r, shared in pairs:
        so = _side(o, score_claim(ds, rec, o) if o else None)
        sa = _side(a, score_claim(ds, rec, a) if a else None)
        kind = "pair" if o and a else ("owner_single" if o else "assistant_single")
        diff = differing(o, a) if o and a else []
        qp = quantity_parts(o, a) if o and a and "quantity" in diff else []
        if kind == "pair" and not diff:                  # both quantities null: never matched (Log #101)
            diff = ["none: both quantity null, never matched"]
        if kind == "pair":
            freq.update(diff)
            combos["+".join(diff)] += 1
        row = {"kind": kind, "pair_rule": r, "shared_number_phrase": shared, "explanation_day": (o or a)["day_ref"],
               "differing_fields": "+".join(diff), "quantity_parts_differing": "+".join(qp)}
        row.update({f"owner_{k}": v for k, v in so.items()})
        row.update({f"assistant_{k}": v for k, v in sa.items()})
        rows.append(row)
    guard_write(folder)                                   # frozen run folders are read-only (R59)
    with open(folder / "adjudication_pairs_view.csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(BANNER + "\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    n = Counter(r["kind"] for r in rows)
    summary = {"display_only": BANNER[2:], "pairing_rule": __doc__.split("Pairing rule (display only), ")[1].strip(),
               "counts": {"pairs": n["pair"], "owner_singles": n["owner_single"],
                          "assistant_singles": n["assistant_single"],
                          "owner_only_total": len(owner_only), "assistant_only_total": len(assistant_only)},
               "differing_fields_per_field": dict(freq.most_common()),
               "differing_fields_combinations": dict(combos.most_common())}
    (folder / "adjudication_pairs_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                            encoding="utf-8", newline="\n")
    return summary


if __name__ == "__main__":
    s = main(sys.argv[1])
    print(json.dumps({k: v for k, v in s.items() if k not in ("pairing_rule", "display_only")}, indent=2))
