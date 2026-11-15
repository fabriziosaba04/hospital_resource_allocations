"""Expand compact claim entries (a Python batch file defining CLAIMS) and append them to the R1 spec.

usage: python add_claims.py <batch.py> <spec.json>
Compact keys: day, field, text, q, rel, v, cat, basis, deps (abbrev list), levels, alloc, cmp, term, alt, note.
alloc / cmp: "cur" = in effect at the start of the day ({"in_effect": day-1}), "dec" = {"decided": day},
"prevday" = {"in_effect": day} used with a past-tense claim whose day is already day-1, or a dict.
"""
import json
import runpy
import sys
from pathlib import Path

DEP = {"C": "cardiology", "IM": "internal_medicine", "N": "neurology", "O": "orthopedics"}
ORDER = ["cardiology", "internal_medicine", "neurology", "orthopedics"]


def alloc(spec, day):
    if spec is None:
        return None
    if spec == "cur":
        return {"in_effect": day - 1}
    if spec == "dec":
        return {"decided": day}
    if spec == "prevday":
        return {"in_effect": day}
    if isinstance(spec, dict) and "B" in spec:
        return {"beds": dict(zip(ORDER, spec["B"])), "nurses": dict(zip(ORDER, spec["N"]))}
    return spec


def expand(c, n):
    day = c["day"]
    q = {"name": c["q"]} if c.get("q") else None
    if q is not None:
        if c.get("deps"):
            q["departments"] = [DEP[d] for d in c["deps"]]
        if c.get("levels"):
            q["levels"] = c["levels"]
        for k in ("patient_id", "department", "level", "arrival_day", "days"):
            if k in c:
                q[k] = c[k]
    out = {"id": f"R1-D{day:02d}-{n:02d}", "author": "ALLOCATOR", "finding": "universe", "field": c["field"],
           "text": c["text"], "day": c.get("qday", day), "allocation": alloc(c.get("alloc"), day),
           "quantity": q, "relation": c.get("rel"), "value": c.get("v"), "category": c["cat"],
           "basis": c["basis"], "rubric_term": c.get("term")}
    if c.get("cmp") is not None:
        out["compare_allocation"] = alloc(c["cmp"], day)
    if c.get("rival"):                      # spare/free: rival reading empty_beds (owner decision §11 #59)
        out["rubric_term"] = c.get("term") or ("free" if c["q"] == "free_beds" else "spare")
        alt = {"quantity": {**q, "name": "empty_beds"}}
        if c.get("rival_alloc"):
            alt["allocation"] = alloc(c["rival_alloc"], day)
        out["alternative_reading"] = alt
    if c.get("alt"):
        out["alternative_reading"] = c["alt"]
    if c.get("note"):
        out["note"] = c["note"]
    return out


def main():
    batch = runpy.run_path(sys.argv[1])["CLAIMS"]
    path = Path(sys.argv[2])
    spec = json.loads(path.read_text(encoding="utf-8"))
    days = sorted({c["day"] for c in batch})
    assert not any(c["day"] in days for c in spec["claims"]), "days already present"
    counter = {}
    for c in batch:
        counter[c["day"]] = counter.get(c["day"], 0) + 1
        spec["claims"].append(expand(c, counter[c["day"]]))
    path.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for d in days:
        cs = [c for c in batch if c["day"] == d]
        print(d, len(cs), "copied", sum(c["basis"] == "copied" for c in cs),
              "derived", sum(c["basis"] == "derived" for c in cs))


if __name__ == "__main__":
    main()
