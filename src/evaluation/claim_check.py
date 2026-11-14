"""Claim-by-claim verification of explanation findings (EVALUATION_PLAN.md §4; owner decision §11 #48).

A finding is split into atomic claims, by the ALLOCATOR (quoted in its explanation) or by the CHECKER (its own
assertion). Each numeric claim names a quantity on a day under an allocation; the quantity is recomputed with
the what-if engine on that day's state, rebuilt from the run records (holders = the previous day's final bed
assignment), never read off the explanation. Each claim is scored correct, wrong or unverifiable.

    uv run python -m src.evaluation.claim_check <run_id>      # reads <eval_dir>/explanation_claims_spec.json

Quantities (summed over `departments`, default all):
  empty_beds             allocated beds minus patients placed in them
  overflow               present patients without a bed, at `levels`
  covered_need           nursing need covered, at `levels` (in need units)
Relations: eq, ne, le, ge (with `value`); `le_alloc` / `ge_alloc` compare with the same quantity under
`compare_allocation`.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

from src.environment.whatif import DayContext, simulate
from src.utils.constants import DEPARTMENTS

from .audit import load_records
from .dataset import ROOT, load_dataset

VERDICTS = ("correct", "wrong", "unverifiable")


def day_context(ds, rec, day: int) -> DayContext:
    prev = rec.beds_initial if day == 1 else rec.beds_final[day - 1]
    present = ds.present(day)
    ids = {p.patient_id for p in present}
    holders = {pid for pid, v in prev["patients"].items() if v["status"] == "in_bed" and pid in ids}
    return DayContext(day, tuple(present), frozenset(holders), ds.pool_beds[day], ds.pool_nurses[day],
                      ds.max_beds, ds.env)


def resolve_allocation(rec, spec) -> tuple[dict, dict]:
    """`{"in_effect": d}` (the allocation in effect at the end of day d; 0 = the initial allocation),
    `{"decided": d}` (the same as in_effect, named for readability), or explicit `{"beds": …, "nurses": …}`,
    optionally with `{"base": {...}, "beds"/"nurses": override}`."""
    if "base" in spec:
        beds, nurses = resolve_allocation(rec, spec["base"])
        return dict(spec.get("beds", beds)), dict(spec.get("nurses", nurses))
    for key in ("in_effect", "decided"):
        if key in spec:
            d = spec[key]
            a = rec.initial if d == 0 else rec.alloc[d]
            return dict(a["beds"]), dict(a["nurses"])
    return dict(spec["beds"]), dict(spec["nurses"])


def quantity(ds, rec, day: int, alloc_spec, q: dict) -> Fraction | int | None:
    beds, nurses = resolve_allocation(rec, alloc_spec)
    ctx = day_context(ds, rec, day)
    res = simulate(beds, nurses, ctx)
    if res.assignment is None:
        return None
    deps = q.get("departments", list(DEPARTMENTS))
    levels = q.get("levels", [1, 2, 3])
    if q["name"] == "empty_beds":
        placed = {d: 0 for d in DEPARTMENTS}
        for p in ctx.present:
            if p.patient_id in res.assignment.in_bed:
                placed[p.department] += 1
        return sum(beds[d] - placed[d] for d in deps)
    if q["name"] == "overflow":
        return sum(res.overflow[d][k] for d in deps for k in levels)
    if q["name"] == "covered_need":
        return sum(Fraction(res.covered[d][k]) for d in deps for k in levels)
    return None


def _num(x):
    return None if x is None else (float(x) if isinstance(x, Fraction) else x)


def score_claim(ds, rec, c: dict) -> dict:
    if c.get("quantity") is None:
        return {**c, "computed": None, "verdict": "unverifiable"}
    v = quantity(ds, rec, c["day"], c["allocation"], c["quantity"])
    if v is None:
        return {**c, "computed": None, "verdict": "unverifiable"}
    rel = c["relation"]
    if rel in ("le_alloc", "ge_alloc"):
        w = quantity(ds, rec, c["day"], c["compare_allocation"], c["quantity"])
        ok = (v <= w) if rel == "le_alloc" else (v >= w)
        return {**c, "computed": _num(v), "computed_compare": _num(w), "verdict": "correct" if ok else "wrong"}
    target = Fraction(str(c["value"]))
    ok = {"eq": v == target, "ne": v != target, "le": v <= target, "ge": v >= target}[rel]
    return {**c, "computed": _num(v), "verdict": "correct" if ok else "wrong"}


def score(run_id: str, spec_path: Path | None = None, results_root: Path = ROOT / "results") -> dict:
    alloc_dir = results_root / "allocations" / run_id
    eval_dir = results_root / "evaluations" / run_id
    m = json.loads((alloc_dir / "run_manifest.json").read_text(encoding="utf-8"))
    data_root = Path(m["data_root"])
    ds = load_dataset(m["dataset_id"], data_root)
    rec = load_records(alloc_dir)
    spec = json.loads((spec_path or eval_dir / "explanation_claims_spec.json").read_text(encoding="utf-8"))
    claims = [score_claim(ds, rec, c) for c in spec["claims"]]
    summary = {}
    for author in ("ALLOCATOR", "CHECKER"):
        mine = [c for c in claims if c["author"] == author]
        summary[author] = {v: sum(1 for c in mine if c["verdict"] == v) for v in VERDICTS}
    findings = {}
    for c in claims:
        f = findings.setdefault(c["finding"], {"ALLOCATOR": {}, "CHECKER": {}})
        f[c["author"]][c["id"]] = c["verdict"]
    for f in findings.values():
        # a finding is valid only if some ALLOCATOR claim it disputes is wrong (EVALUATION_PLAN.md §4)
        f["finding_valid"] = any(v == "wrong" for v in f["ALLOCATOR"].values())
    return {"run_id": run_id, "claims": claims, "summary": summary, "findings": findings}


if __name__ == "__main__":
    out = score(sys.argv[1])
    eval_dir = ROOT / "results" / "evaluations" / sys.argv[1]
    (eval_dir / "explanation_claims.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8",
                                                      newline="\n")
    print(json.dumps({"summary": out["summary"], "findings": out["findings"]}, indent=2))
