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
Day quantities (no allocation): pool_beds, pool_nurses, max_beds, census, holders, queue, free_beds,
requirement, mean_arrivals, patient, need. Allocation quantities: beds, nurses, empty_beds, overflow,
covered_need, shortage, patient_in_bed, holders_cut, spare_beds (allocated beds minus holders).
Relations: eq, ne, le, ge (with `value`; counts are exact, tolerance 0); in_range (`value` = [lo, hi], inclusive);
round (a stated decimal compared at its
own precision); le_alloc / ge_alloc / eq_alloc compare with the same quantity under `compare_allocation`;
lex_le_alloc ("no better", §11 #57) compares nursing need covered by tier (levels >= 3, >= 2, >= 1, over the
quantity's departments) lexicographically: correct if the allocation is not better than `compare_allocation`.
Each claim may carry a `category`; the pre-registered universe (EVALUATION_PLAN.md §4) is the categories
beds, empty_beds, overflow, nurse_coverage, pool.

Stratification (owner review 2026-11-14, EVALUATION_PLAN.md §4 items 7-9), all optional per claim:
  basis                  "copied" (one cell of a tool result the ALLOCATOR received that day, for the same
                         quantity, departments, levels and allocation) or "derived" (anything else)
  rubric_term            the defined term the claim uses ("empty", "spare", "covered", "no better", ...), or
                         null; a wrong claim is rubric-dependent only if `verdict_alternative` is correct
  alternative_reading    overrides of quantity / relation / value / compare_allocation under the rival reading
                         of `rubric_term`; scored as `verdict_alternative`, descriptive only
`extraction_recall(a, b)` compares two extractions of the same days, claim by claim, by `basis`.
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
from src.utils.paths import guard_write, long_path, recomputed_dir

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


DAY_QUANTITIES = ("pool_beds", "pool_nurses", "max_beds", "census", "holders", "queue", "free_beds",
                  "requirement", "mean_arrivals", "patient", "need")


def day_quantity(ds, rec, day: int, q: dict):
    """Quantities of the day's state before the decision (no allocation needed)."""
    from src.environment.nurses import requirement
    ctx = day_context(ds, rec, day)
    deps = q.get("departments", list(DEPARTMENTS))
    levels = q.get("levels", [1, 2, 3])
    n = q["name"]
    if n == "pool_beds":
        return ctx.pool_beds
    if n == "pool_nurses":
        return ctx.pool_nurses
    if n == "max_beds":
        return ctx.max_beds
    if n == "census":
        return sum(1 for p in ctx.present if p.department in deps and p.complexity in levels)
    if n == "holders":
        return sum(1 for p in ctx.holders if p.department in deps and p.complexity in levels)
    if n == "need":                                      # nursing need (N1 weights), in need units
        nd = ctx.needs()
        return sum(Fraction(nd[d][k]) for d in deps for k in levels)
    if n == "queue":                                     # present patients without a bed held from yesterday
        return sum(1 for p in ctx.present if p.patient_id not in ctx.holder_ids and p.department in deps
                   and p.complexity in levels)
    if n == "free_beds":                                 # pool minus holders
        return ctx.pool_beds - len(ctx.holders)
    if n == "requirement":
        c = ctx.counts()
        return sum(requirement(c[d][1], c[d][2], c[d][3], ctx.weights) for d in deps)
    if n == "mean_arrivals":                             # observed arrivals per day over days lo..hi (<= day)
        lo, hi = q["days"]
        ids = {}
        for t in range(1, hi + 1):
            for p in ds.present(t):
                ids[p.patient_id] = p
        arr = sum(1 for p in ids.values() if p.department in deps and lo <= p.arrival_day <= hi)
        return Fraction(arr, hi - lo + 1)
    if n == "patient":                                   # 1 if every stated attribute matches the registry
        p = next((x for x in ctx.present if x.patient_id == q["patient_id"]), None)
        if p is None:
            return 0
        ok = all(getattr(p, {"level": "complexity"}.get(k, k)) == v for k, v in q.items()
                 if k in ("department", "level", "arrival_day"))
        return int(ok)
    return None


def quantity(ds, rec, day: int, alloc_spec, q: dict) -> Fraction | int | None:
    if q["name"] in DAY_QUANTITIES:
        return day_quantity(ds, rec, day, q)
    beds, nurses = resolve_allocation(rec, alloc_spec)
    ctx = day_context(ds, rec, day)
    deps = q.get("departments", list(DEPARTMENTS))
    levels = q.get("levels", [1, 2, 3])
    # statements of the allocation itself need no assignment, so they are compared even when the allocation
    # fails validation that day (the in-effect allocation on a shock day; R1 extraction README)
    if q["name"] == "beds":
        return sum(beds[d] for d in deps)
    if q["name"] == "nurses":
        return sum(nurses[d] for d in deps)
    if q["name"] == "spare_beds":                        # allocated beds not held from yesterday ("free", "spare")
        return sum(beds[d] for d in deps) - sum(1 for p in ctx.holders if p.department in deps)
    res = simulate(beds, nurses, ctx)
    if res.assignment is None:
        return None
    if q["name"] == "shortage":
        return sum(Fraction(res.shortage[d][k]) for d in deps for k in levels)
    if q["name"] == "patient_in_bed":
        return int(q["patient_id"] in res.assignment.in_bed)
    if q["name"] == "holders_cut":                       # holders who lose their bed (shock cut)
        return sum(1 for p in ctx.holders if p.patient_id not in res.assignment.in_bed and p.department in deps
                   and p.complexity in levels)
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
    out = _score_one(ds, rec, c)
    if c.get("alternative_reading"):
        alt = _score_one(ds, rec, {**c, **c["alternative_reading"]})
        out["verdict_alternative"], out["computed_alternative"] = alt["verdict"], alt["computed"]
    return out


def _score_one(ds, rec, c: dict) -> dict:
    if c.get("quantity") is None:
        return {**c, "computed": None, "verdict": "unverifiable"}
    v = quantity(ds, rec, c["day"], c.get("allocation"), c["quantity"])
    if v is None:
        return {**c, "computed": None, "verdict": "unverifiable"}
    rel = c["relation"]
    if rel == "lex_le_alloc":                # "no better" (§11 #57): not lexicographically better by tier 3, 2, 1
        def tiers(alloc):
            return tuple(quantity(ds, rec, c["day"], alloc, {**c["quantity"], "name": "covered_need",
                                                             "levels": list(range(j, 4))}) for j in (3, 2, 1))
        a, b = tiers(c.get("allocation")), tiers(c["compare_allocation"])
        if None in a or None in b:
            return {**c, "computed": None, "verdict": "unverifiable"}
        return {**c, "computed": [_num(x) for x in a], "computed_compare": [_num(x) for x in b],
                "verdict": "correct" if a <= b else "wrong"}
    if rel in ("le_alloc", "ge_alloc", "eq_alloc"):
        w = quantity(ds, rec, c["day"], c["compare_allocation"], c["quantity"])
        ok = {"le_alloc": v <= w, "ge_alloc": v >= w, "eq_alloc": v == w}[rel]
        return {**c, "computed": _num(v), "computed_compare": _num(w), "verdict": "correct" if ok else "wrong"}
    if rel == "in_range":                    # a stated range "[lo, hi]" is correct if the value lies inside (item 2)
        lo, hi = (Fraction(str(x)) for x in c["value"])
        return {**c, "computed": _num(v), "verdict": "correct" if lo <= v <= hi else "wrong"}
    target = Fraction(str(c["value"]))
    if rel == "round":                       # a stated decimal is compared at its own precision ("about 2.7")
        places = len(str(c["value"]).split(".")[1]) if "." in str(c["value"]) else 0
        half = Fraction(1, 2 * 10 ** places)
        ok = target - half <= v < target + half
        return {**c, "computed": _num(v), "verdict": "correct" if ok else "wrong"}
    ok = {"eq": v == target, "ne": v != target, "le": v <= target, "ge": v >= target}[rel]
    return {**c, "computed": _num(v), "verdict": "correct" if ok else "wrong"}


def score(run_id: str, spec_path: Path | None = None, results_root: Path = ROOT / "results") -> dict:
    alloc_dir = long_path(results_root / "allocations" / run_id)        # Log #117
    eval_dir = long_path(results_root / "evaluations" / run_id)
    m = json.loads((alloc_dir / "run_manifest.json").read_text(encoding="utf-8"))
    from .run_report import resolve_data_root       # the clone or the old fixture path may not exist here
    ds = load_dataset(m["dataset_id"], resolve_data_root(m))
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
    out = {"run_id": run_id, "claims": claims, "summary": summary, "findings": findings,
           "stratified": stratify(claims)}
    if "disputed_by_checker" in spec:
        out["checker_on_claims"] = checker_on_claims(claims, spec["disputed_by_checker"])
    return out


def checker_on_claims(claims: list[dict], disputed: dict[str, str]) -> dict:
    """CHECKER against the full universe of scored ALLOCATOR claims (EVALUATION_PLAN.md §4): `disputed` maps
    each ALLOCATOR claim id the CHECKER contested to the CHECKER issue that contests it."""
    alloc = {c["id"]: c["verdict"] for c in claims if c["author"] == "ALLOCATOR"}
    wrong = {i for i, v in alloc.items() if v == "wrong"}
    contested = set(disputed) & set(alloc)
    hit = wrong & contested
    return {"wrong_claims": len(wrong), "contested": len(contested), "caught": len(hit),
            "recall": f"{len(hit)}/{len(wrong)}", "precision": f"{len(hit)}/{len(contested)}",
            "wrong_disputes": sorted(contested - wrong - {i for i, v in alloc.items() if v == "unverifiable"}),
            "missed": sorted(wrong - contested),
            "contested_unverifiable": sorted(i for i in contested if alloc[i] == "unverifiable"),
            "disputes_outside_universe": sorted(set(disputed) - set(alloc))}


def stratify(claims: list[dict]) -> dict:
    """ALLOCATOR verdicts by basis, and its wrong claims by rubric term (EVALUATION_PLAN.md §4 items 8-9).
    Counts only; a claim without `basis` is counted as "unclassified"."""
    alloc = [c for c in claims if c["author"] == "ALLOCATOR"]
    by_basis = {}
    for c in alloc:
        b = by_basis.setdefault(c.get("basis") or "unclassified", {v: 0 for v in VERDICTS})
        b[c["verdict"]] += 1
    wrong = [c for c in alloc if c["verdict"] == "wrong"]
    by_term = {}
    for c in wrong:
        t = c.get("rubric_term") or "arithmetic"
        e = by_term.setdefault(t, {"wrong": 0, "correct_under_alternative": 0, "ids": []})
        e["wrong"] += 1
        e["correct_under_alternative"] += c.get("verdict_alternative") == "correct"
        e["ids"].append(c["id"])
    # rubric-dependent = wrong under the rubric's reading but correct under the rival one; a wrong claim that
    # uses a defined term but is wrong under both readings (or has no rival reading) is not counted as semantic
    flips = sorted(c["id"] for c in wrong if c.get("verdict_alternative") == "correct")
    return {"allocator_by_basis": by_basis, "wrong_by_rubric_term": by_term,
            "wrong_rubric_dependent": f"{len(flips)}/{len(wrong)}", "rubric_dependent_ids": flips}


def claim_key(c: dict) -> str:
    """What makes two extractions the same claim: day, quantity, allocation, relation and stated value.
    The field is left out because a figure repeated in another field is extracted once (rubric item 2)."""
    return json.dumps([c["day"], c.get("quantity"), c.get("allocation"), c.get("compare_allocation"),
                       c.get("relation"), None if c.get("value") is None else str(c["value"])], sort_keys=True)


def extraction_recall(a: list[dict], b: list[dict], days=None) -> dict:
    """Two-way extraction recall (owner check 2(a)): the share of each extractor's ALLOCATOR claims that the
    other also extracted, by the reference extractor's `basis`. Written as counts."""
    def pick(cs):
        return [c for c in cs if c["author"] == "ALLOCATOR" and (days is None or c["day"] in days)]
    a, b = pick(a), pick(b)
    def one(ref, other):
        keys = {claim_key(c) for c in other}
        out = {}
        for c in ref:
            e = out.setdefault(c.get("basis") or "unclassified", [0, 0])
            e[0] += claim_key(c) in keys
            e[1] += 1
        res = {k: f"{v[0]}/{v[1]}" for k, v in sorted(out.items())}
        res["missed"] = sorted(c["id"] for c in ref if claim_key(c) not in keys)
        return res
    return {"a_found_by_b": one(a, b), "b_found_by_a": one(b, a)}


if __name__ == "__main__":
    out = score(sys.argv[1])
    eval_dir = guard_write(recomputed_dir(sys.argv[1]))          # never the run folder (R59)
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "explanation_claims.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8",
                                                      newline="\n")
    print(json.dumps({"summary": out["summary"], "findings": out["findings"]}, indent=2))
