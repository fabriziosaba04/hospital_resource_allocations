"""The owner's independent claim extraction (EVALUATION_PLAN.md §4 item 7a): conversion and comparison.

The owner's CSV is frozen and never edited. `convert` maps each row to a `claim_check` claim with fixed rules
and two committed tables in the same folder: `mapping_quantity.csv` (the free-text Quantity column) and
`row_overrides.csv` (row-level allocations the owner's columns do not determine). Every mapping that is not
mechanical is listed in `non_mechanical_mappings.csv`.

    uv run python -m src.evaluation.owner_claims R1

Rules (code in brackets is written to each converted claim's `mapping`):
  [D1] Departments: "all" or blank -> all (omitted); CA / IM / NE / OR -> department names; separators
       "," "+" "-" and spaces.
  [T1] Tier: "all" or blank -> all levels (omitted); "k" -> [k]; "a-b" -> [a..b].
  [Q1] Quantity: `mapping_quantity.csv`. [Q2] "nurse requirement" with a tier restriction and a decimal value
       -> `need` (owner decision §11 #61 B: an unrounded tier sum is in the universe; the ceiling is not). [Q0] no claim_check quantity ->
       quantity null (unmapped, not mechanical).
  [A0] Day quantities (pools, holders, queue, need) take no allocation: null, whatever the owner wrote.
  [A1] "in effect" -> {"in_effect": d-1}. [A2] "chosen" -> {"decided": d}.
  [A3] "overflow" with allocation N/A in the situation or information_used field -> `queue` (the patients
       without a held bed before the decision; not mechanical).
  [A4] Allocation N/A on any other allocation quantity: `row_overrides.csv` (not mechanical), else quantity
       null (unmapped).
  [V1] "'=" with an integer -> eq. [V2] "'=" with a decimal -> round (rubric item 2: compared at its own
       precision). [V3] "covered" with 0 -> `shortage` eq 0 (rubric: covered = shortage 0). [V4] "range" with
       ">= n" / "<= n" -> ge / le n.
  [P1] "patient in overflow" with a patient id -> `patient_in_bed` of that patient eq 0 (department and tier
       are attributes of the patient, not filters).
  [U1] Unverifiable other than "no" -> quantity, relation and value null.
Rows with Category out_of_universe are not converted; `compare` lists them separately.

`compare` applies the approved same-claim rule (`claim_check.claim_key`: day, quantity, allocation,
compare_allocation, relation, stated value; field ignored) through `claim_check.extraction_recall`, after two
normalisations that do not change any claim's meaning: department and level lists in a fixed order, and a
claim with quantity null given a key of its own (it states no quantity, so it cannot be the same quantity as
another claim; the count the unchanged key would give is reported next to it).
"""

from __future__ import annotations

import csv
import difflib
import json
import re
import sys
from pathlib import Path

from src.utils.constants import DEPARTMENTS

from .claim_check import claim_key, extraction_recall
from .dataset import ROOT

DEP_CODES = {"CA": "cardiology", "IM": "internal_medicine", "NE": "neurology", "OR": "orthopedics"}
DAY_QUANTITIES = {"pool_beds", "pool_nurses", "holders", "queue", "need", "free_beds"}
FILE = "owner_claims_d03_d08_d18.csv"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _departments(s: str) -> list[str] | None:
    s = s.strip()
    if s.lower() in ("", "all"):
        return None
    codes = [t for t in re.split(r"[,+\-\s]+", s) if t]
    return sorted({DEP_CODES[t.upper()] for t in codes}, key=DEPARTMENTS.index)


def _levels(s: str) -> list[int] | None:
    s = s.strip().lower()
    if s in ("", "all"):
        return None
    if "-" in s:
        lo, hi = (int(x) for x in s.split("-"))
        return list(range(lo, hi + 1))
    return [int(s)]


def _number(s: str):
    return float(s) if "." in s else int(s)


def convert(folder: Path) -> tuple[list[dict], list[dict]]:
    qmap = {_norm(r["owner_quantity"]): r for r in csv.DictReader(open(folder / "mapping_quantity.csv",
                                                                       encoding="utf-8"))}
    overrides = {int(r["row"]): r for r in csv.DictReader(open(folder / "row_overrides.csv", encoding="utf-8"))}
    rows = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))
    claims, nonmech = [], []
    for i, r in enumerate(rows, 1):
        if r["Category"].strip() == "out_of_universe":
            continue
        day, rules, why = int(r["Day"]), [], []
        c = {"id": f"OWN-D{day:02d}-r{i:03d}", "author": "ALLOCATOR", "finding": "owner", "owner_row": i,
             "field": r["Field"].strip(), "text": r["Quoted text"].strip(), "day": day,
             "category": r["Category"].strip(), "basis": r["Basis"].strip() or None,
             "rubric_term": None if r["Rubric term"].strip() in ("", "none") else r["Rubric term"].strip(),
             "owner_raw": dict(r)}
        q = {}
        deps, levels = _departments(r["Departments"]), _levels(r["Tier"])
        rules += ["D1", "T1"]
        m = qmap.get(_norm(r["Quantity"]))
        name = m["claim_check_name"] if m else ""
        rules.append("Q1")
        if _norm(r["Quantity"]) == "nurse requirement" and levels:
            rules.append("Q2")
            why.append("Q2: 'nurse requirement' restricted to tiers, stated as a decimal: the unrounded summed need, "
                       "in the universe (owner decision §11 #61 B: only the ceiling is a requirement; the stated "
                       "value is not an integer, so it is not the ceiling)")
        rel, val = r["Relation"].strip().lstrip("'"), r["Value"].strip()
        alloc_txt = r["Allocation"].strip().lower()
        if name and rel == "covered" and val == "0":
            name, relation, value = "shortage", "eq", 0
            rules.append("V3")
        elif name == "patient_in_bed":
            q["patient_id"], relation, value = val, "eq", 0
            deps = levels = None
            rules.append("P1")
        elif rel == "range":
            op, n = re.match(r"([<>]=)\s*(\S+)", val).groups()
            relation, value = {">=": "ge", "<=": "le"}[op], _number(n)
            rules.append("V4")
        elif rel == "=" and val:
            value = _number(val)
            relation = "round" if isinstance(value, float) else "eq"
            rules.append("V2" if relation == "round" else "V1")
        else:
            relation, value = None, None
        alloc = None
        unverifiable = r["Unverifiable"].strip().lower() not in ("", "no")
        if unverifiable:                                 # [U1] first: nothing else is mapped for such a row
            c.update(quantity=None, allocation=None, relation=None, value=None, mapping=rules + ["U1"])
            claims.append(c)
            continue
        if name == "overflow" and alloc_txt == "n/a" and c["field"] in ("situation", "information_used"):
            name = "queue"
            rules.append("A3")
            why.append("A3: overflow with allocation N/A in the situation / information_used field read as the queue")
        if name in DAY_QUANTITIES:
            rules.append("A0")
        elif alloc_txt == "in effect":
            alloc = {"in_effect": day - 1}
            rules.append("A1")
        elif alloc_txt == "chosen":
            alloc = {"decided": day}
            rules.append("A2")
        elif name:
            if i in overrides:
                alloc = json.loads(overrides[i]["allocation"])
                rules.append("A4")
                why.append("A4: " + overrides[i]["reason"])
            else:
                why.append("A4: allocation N/A on an allocation quantity and no override: unmapped")
                name = ""
        if not name:
            if "Q0" not in rules:
                rules.append("Q0")
            if not any(w.startswith("A4") for w in why):
                why.append(f"Q0: no claim_check quantity for '{r['Quantity'].strip()}': unmapped")
        if not name:
            c.update(quantity=None, allocation=None, relation=None, value=None)
        else:
            q = {"name": name, **q}
            if deps:
                q["departments"] = deps
            if levels:
                q["levels"] = levels
            c.update(quantity=q, allocation=alloc, relation=relation, value=value)
        c["mapping"] = rules
        if why:
            c["mapping_not_mechanical"] = why
            nonmech.append({"row": i, "day": day, "field": c["field"], "text": c["text"],
                            "owner_quantity": r["Quantity"].strip(), "owner_allocation": r["Allocation"].strip(),
                            "mapped_to": encoding(c), "reason": " | ".join(why)})
        claims.append(c)
    return claims, nonmech


def _canon(c: dict) -> dict:
    """Comparison copy: list order fixed, and a claim without a quantity keyed on its own id."""
    c = dict(c)
    if c.get("quantity") is None:
        c["quantity"] = {"name": "__no_quantity__", "id": c["id"]}
        return c
    q = dict(c["quantity"])
    if "departments" in q:
        q["departments"] = sorted(q["departments"], key=DEPARTMENTS.index)
    if "levels" in q:
        q["levels"] = sorted(q["levels"])
    c["quantity"] = q
    return c


ABBR = {v: k for k, v in DEP_CODES.items()}


def _alloc_str(a) -> str:
    if a is None:
        return "-"
    if "in_effect" in a:
        return f"in_effect({a['in_effect']})"
    if "decided" in a:
        return f"decided({a['decided']})"
    order = ("cardiology", "internal_medicine", "neurology", "orthopedics")
    b = "/".join(str(a["beds"][d]) for d in order)
    n = "/".join(str(a["nurses"][d]) for d in order)
    return f"beds {b} nurses {n} (CA/IM/NE/OR)"


def encoding(c: dict) -> str:
    q = c.get("quantity")
    if q is None:
        return "quantity null (unverifiable or unmapped)"
    s = q["name"]
    if "patient_id" in q:
        s += f"({q['patient_id']})"
    if "departments" in q:
        s += "[" + ",".join(ABBR[d] for d in sorted(q["departments"], key=DEPARTMENTS.index)) + "]"
    if "levels" in q:
        s += "L" + "".join(map(str, sorted(q["levels"])))
    s += f" | {_alloc_str(c.get('allocation'))} | {c.get('relation')} {c.get('value')}"
    if c.get("compare_allocation"):
        s += f" vs {_alloc_str(c['compare_allocation'])}"
    return s


def _nearest(c: dict, others: list[dict]) -> dict | None:
    """Display aid only (never used for matching): the other side's claim on the same day whose quoted text
    is most similar, if the similarity is at least 0.6 or one text contains the other."""
    best, score = None, 0.0
    a = _norm(c["text"])
    for o in others:
        if o["day_ref"] != c["day_ref"]:
            continue
        b = _norm(o["text"])
        s = 1.0 if (a and b and (a in b or b in a)) else difflib.SequenceMatcher(None, a, b).ratio()
        s += 0.01 * (o.get("field") == c.get("field"))
        if s > score:
            best, score = o, s
    return best if score >= 0.6 else None


def compare(owner: list[dict], spec: list[dict], days: set[int], raw_rows: list[dict]) -> dict:
    # the assistant's ids carry the day of the explanation; a past-tense claim's `day` is d-1 (README)
    mine = [c for c in spec if c["author"] == "ALLOCATOR" and int(c["id"].split("-D")[1][:2]) in days]
    for c in mine:
        c["day_ref"] = int(c["id"].split("-D")[1][:2])
    for c in owner:
        c["day_ref"] = c["day"]
    o_c, m_c = [_canon(c) for c in owner], [_canon(c) for c in mine]
    rec = extraction_recall(o_c, m_c)                    # days already selected; `day` kept as encoded
    # what the unchanged key would give: null-quantity claims of the same day collide
    rec_unchanged = extraction_recall([{**c, "quantity": c["quantity"] if c["quantity"].get("name") !=
                                        "__no_quantity__" else None} for c in o_c],
                                      [{**c, "quantity": c["quantity"] if c["quantity"].get("name") !=
                                        "__no_quantity__" else None} for c in m_c])
    keys_m = {}
    for c in m_c:
        keys_m.setdefault(claim_key(c), []).append(c)
    keys_o = {}
    for c in o_c:
        keys_o.setdefault(claim_key(c), []).append(c)
    basis_pairs = []
    for k, os_ in keys_o.items():
        for o in os_:
            for m in keys_m.get(k, []):
                basis_pairs.append({"owner_row": o["owner_row"], "assistant_id": m["id"], "day": o["day_ref"],
                                    "text_owner": o["text"], "owner": o.get("basis"), "assistant": m.get("basis")})
    agree = sum(p["owner"] == p["assistant"] for p in basis_pairs)
    dup = {"owner": [[c["id"] for c in v] for v in keys_o.values() if len(v) > 1],
           "assistant": [[c["id"] for c in v] for v in keys_m.values() if len(v) > 1]}
    adjud = []
    for side, mine_side, other, keys_other in (("owner_only", o_c, m_c, keys_m), ("assistant_only", m_c, o_c, keys_o)):
        for c in mine_side:
            if claim_key(c) in keys_other:
                continue
            orig = next(x for x in (owner if side == "owner_only" else mine) if x["id"] == c["id"])
            near = _nearest(c, other)
            near_orig = None if near is None else next(x for x in (mine if side == "owner_only" else owner)
                                                       if x["id"] == near["id"])
            o_, a_ = (orig, near_orig) if side == "owner_only" else (near_orig, orig)
            adjud.append({
                "side": side, "day": c["day_ref"],
                "owner_row": "" if o_ is None else o_["owner_row"],
                "owner_field": "" if o_ is None else o_["field"],
                "owner_text": "" if o_ is None else o_["text"],
                "owner_encoding": "" if o_ is None else encoding(o_),
                "assistant_id": "" if a_ is None else a_["id"],
                "assistant_field": "" if a_ is None else a_["field"],
                "assistant_text": "" if a_ is None else a_["text"],
                "assistant_encoding": "" if a_ is None else encoding(a_),
                "counterpart": "none found" if near is None else "nearest text on the other side (display only)",
                "cause": ""})
    oou = []
    for i, r in enumerate(raw_rows, 1):
        if r["Category"].strip() != "out_of_universe":
            continue
        d, t = int(r["Day"]), _norm(r["Quoted text"])
        # the assistant extracted the row if a claim of that day quotes text containing it (or contained in it),
        # or encodes an out-of-universe quantity; fuzzy similarity is not used (short strings collide)
        hits = [c for c in mine if c["day_ref"] == d and ((t and (t in _norm(c["text"]) or _norm(c["text"]) in t))
                or (c.get("quantity") or {}).get("name") in ("census", "requirement", "mean_arrivals", "patient"))]
        oou.append({"row": i, "day": d, "text": r["Quoted text"].strip(), "owner_quantity": r["Quantity"].strip(),
                    "assistant_also_left_out": not hits,
                    "assistant_claims": [{"id": c["id"], "text": c["text"], "encoding": encoding(c)} for c in hits]})
    return {"recall": rec, "recall_if_null_quantities_collide": {k: {b: v for b, v in rec_unchanged[k].items()
                                                                     if b != "missed"} for k in rec_unchanged},
            "basis_agreement": {"matched_pairs": len(basis_pairs), "agree": f"{agree}/{len(basis_pairs)}",
                                "disagree": [p for p in basis_pairs if p["owner"] != p["assistant"]]},
            "duplicate_keys_within_a_side": dup, "out_of_universe_owner_rows": oou, "adjudication": adjud}


def main(run_id: str) -> None:
    folder = ROOT / "results" / "evaluations" / run_id / "owner_extraction"
    claims, nonmech = convert(folder)
    (folder / "owner_claims_converted.json").write_text(
        json.dumps({"run_id": run_id, "source": FILE, "claims": claims}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    with open(folder / "non_mechanical_mappings.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row", "day", "field", "text", "owner_quantity", "owner_allocation",
                                          "mapped_to", "reason"], lineterminator="\n")
        w.writeheader()
        w.writerows(nonmech)
    spec = json.loads((folder.parent / "explanation_claims_spec.json").read_text(encoding="utf-8"))["claims"]
    raw = list(csv.DictReader(open(folder / FILE, encoding="utf-8-sig")))
    days = sorted({c["day"] for c in claims})
    out = compare(claims, spec, set(days), raw)
    adjud = out.pop("adjudication")
    with open(folder / "adjudication_7a.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(adjud[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(adjud)
    out["adjudication_rows"] = {"owner_only": sum(a["side"] == "owner_only" for a in adjud),
                                "assistant_only": sum(a["side"] == "assistant_only" for a in adjud)}
    out["days"] = days
    (folder / "comparison_7a.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("recall", "recall_if_null_quantities_collide", "adjudication_rows")},
                     indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
