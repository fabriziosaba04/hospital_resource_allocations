"""Deterministic audit (AGENTS.md §6, EVALUATION_PLAN.md §3–§4, §7).

Independent of any LLM output, and independent of the environment where it matters:
  - hard constraints, N1, coverage C1 and the bed-assignment replay are re-implemented here
    (integer hundredths via Decimal, not the environment's Fraction code);
  - bed tier gaps use the closed form (Max_j), cross-checked against the environment's pairing detector;
  - nurse tier maxima and the lexicographic rounding floor are found by enumerating every integer
    allocation, cross-checked in tests against the environment's closed form.
The only environment functions used are the pairing detector (the second side of a cross-check) and the
repair rule (the stability reference, which is defined as that rule).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.environment.bed_assignment import BedAssignment
from src.environment.clinical import bed_pairs
from src.environment.repair import repair
from src.environment.types import Patient
from src.utils.constants import DEPARTMENTS, LEVELS

from .dataset import Dataset
from src.utils.paths import long_path

SCALE = 100   # need is held in integer hundredths of a nurse


# ----------------------------------------------------------------------------- own primitives

def weights_hundredths(env: dict) -> dict[int, int]:
    out = {}
    for k in LEVELS:
        w = Decimal(str(env[f"w_L{k}"])) * SCALE
        if w != w.to_integral_value():
            raise ValueError(f"w_L{k} has more than two decimals; the audit's integer scale would be inexact")
        out[k] = int(w)
    return out


def ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


@lru_cache(maxsize=None)
def compositions(total: int) -> np.ndarray:
    """Every (N_1..N_4) of non-negative integers summing to `total`."""
    rows = [(a, b, c, total - a - b - c) for a in range(total + 1) for b in range(total + 1 - a)
            for c in range(total + 1 - a - b)]
    return np.array(rows, dtype=np.int64)


def own_assignment(beds: dict, present: list[Patient], holder_ids: set[str]) -> set[str]:
    """Independent re-implementation of CLAUDE.md §10.F for the replay check."""
    in_bed: set[str] = set()
    for d in DEPARTMENTS:
        mine = [p for p in present if p.department == d]
        keep = [p for p in mine if p.patient_id in holder_ids]
        wait = [p for p in mine if p.patient_id not in holder_ids]
        # keep the highest-priority holders: cut from (low level, recent arrival, high id)
        keep.sort(key=lambda p: (p.complexity, -p.arrival_day, -int(p.patient_id[1:])), reverse=True)
        keep = keep[: beds[d]]
        wait.sort(key=lambda p: (-p.complexity, p.arrival_day, int(p.patient_id[1:])))
        in_bed |= {p.patient_id for p in keep} | {p.patient_id for p in wait[: max(0, beds[d] - len(keep))]}
    return in_bed


def own_hard_constraints(beds, nurses, pool_b, pool_n, max_beds, occ) -> list[str]:
    errs = []
    for name, a in (("beds", beds), ("nurses", nurses)):
        if sorted(a) != sorted(DEPARTMENTS):
            return [f"{name}: wrong departments"]
        if not all(type(a[d]) is int for d in DEPARTMENTS):
            errs.append(f"{name}: non-integer value")
    if errs:
        return errs
    if sum(beds.values()) != pool_b:
        errs.append(f"bed conservation: {sum(beds.values())} != {pool_b}")
    if sum(nurses.values()) != pool_n:
        errs.append(f"nurse conservation: {sum(nurses.values())} != {pool_n}")
    errs += [f"bed bounds {d}={beds[d]}" for d in DEPARTMENTS if not 0 <= beds[d] <= max_beds]
    errs += [f"nurse bounds {d}={nurses[d]}" for d in DEPARTMENTS if nurses[d] < 0]
    cut = sum(max(0, occ[d] - beds[d]) for d in DEPARTMENTS)
    short = sum(occ.values()) - pool_b
    if short <= 0 and cut > 0:
        errs.append(f"eviction: {cut} occupied beds removed without a shortfall")
    if short > 0 and cut != short:
        errs.append(f"relaxed no-eviction: {cut} cut, shortfall {short}")
    return errs


def bed_tier_max(holders: list[Patient], nonholders: list[Patient], pool_beds: int, cap: int) -> dict[int, int]:
    """Max_j: the most level->=j patients any feasible allocation can have in a bed (EVALUATION_PLAN.md §3.1)."""
    occ = {d: sum(1 for p in holders if p.department == d) for d in DEPARTMENTS}
    shortfall = sum(occ.values()) - pool_beds
    out = {}
    for j in LEVELS:
        h_ge = sum(1 for p in holders if p.complexity >= j)
        if shortfall > 0:                                   # shock day: cut the lowest-level holders
            out[j] = h_ge - max(0, shortfall - (len(holders) - h_ge))
        else:
            q = {d: sum(1 for p in nonholders if p.department == d and p.complexity >= j) for d in DEPARTMENTS}
            out[j] = h_ge + min(-shortfall, sum(min(q[d], cap - occ[d]) for d in DEPARTMENTS))
    return out


# ----------------------------------------------------------------------------- records

def read_jsonl(path: Path) -> list[dict]:
    with open(long_path(path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@dataclass
class RunRecords:
    run_id: str
    initial: dict                      # allocation line written by the initial rule
    alloc: dict[int, dict]             # day -> allocation in effect (last line of the day)
    beds_initial: dict                 # day-1 initial-stage bed assignment line
    beds_final: dict[int, dict]
    decisions: list[dict] = field(default_factory=list)


def load_records(run_dir: Path) -> RunRecords:
    run_dir = long_path(run_dir)                       # Log #117
    alloc_lines = read_jsonl(run_dir / "allocation_state.jsonl")
    bed_lines = read_jsonl(run_dir / "bed_assignment_state.jsonl")
    initial = next(x for x in alloc_lines if x["source"] == "initial_rule")
    alloc = {}
    for x in alloc_lines:
        if x["source"] != "initial_rule":
            alloc[x["day"]] = x
    beds_initial = next(x for x in bed_lines if x["stage"] == "initial")
    beds_final = {x["day"]: x for x in bed_lines if x["stage"] == "final"}
    dh = run_dir / "decision_history.jsonl"
    return RunRecords(initial["run_id"], initial, alloc, beds_initial, beds_final,
                      read_jsonl(dh) if dh.exists() else [])


# ----------------------------------------------------------------------------- per-day audit

def _issue(day, category, level, kind, detail):
    return {"day": day, "category": category, "level": level, "type": kind, "detail": detail}


def audit_day(ds: Dataset, rec: RunRecords, day: int, w: dict[int, int]) -> dict:
    present = ds.present(day)
    by_id = {p.patient_id: p for p in present}
    prev_bed_line = rec.beds_initial if day == 1 else rec.beds_final[day - 1]
    holder_ids = {pid for pid, v in prev_bed_line["patients"].items()
                  if v["status"] == "in_bed" and pid in by_id}
    a = rec.alloc[day]
    beds, nurses = a["beds"], a["nurses"]
    P_B, P_N, cap = ds.pool_beds[day], ds.pool_nurses[day], ds.max_beds
    in_bed = {pid for pid, v in rec.beds_final[day]["patients"].items() if v["status"] == "in_bed"}
    issues = []

    occ = {d: 0 for d in DEPARTMENTS}
    for pid in holder_ids:
        occ[by_id[pid].department] += 1
    hc = own_hard_constraints(beds, nurses, P_B, P_N, cap, occ)
    for e in hc:
        issues.append(_issue(day, "violation", "Critical", "hard_constraint_in_effect", e))
    replay_ok = own_assignment(beds, present, holder_ids) == in_bed and set(rec.beds_final[day]["patients"]) == set(by_id)
    if not replay_ok:
        issues.append(_issue(day, "violation", "Critical", "replay_mismatch", "stored bed assignment differs from replay"))

    # ---- counts
    n = {d: {k: 0 for k in LEVELS} for d in DEPARTMENTS}
    of = {d: {k: 0 for k in LEVELS} for d in DEPARTMENTS}
    for p in present:
        n[p.department][p.complexity] += 1
        if p.patient_id not in in_bed:
            of[p.department][p.complexity] += 1

    # ---- A1: bed tier gaps (closed form) and pairs (environment detector)
    shock = sum(occ.values()) > P_B
    holders = [by_id[i] for i in holder_ids]
    nonh = [p for p in present if p.patient_id not in holder_ids]
    M = P_B - sum(occ.values())
    max_b = bed_tier_max(holders, nonh, P_B, cap)
    ach_b = {j: sum(1 for i in in_bed if by_id[i].complexity >= j) for j in LEVELS}
    gap_b = {j: max_b[j] - ach_b[j] for j in LEVELS}
    asg = BedAssignment(frozenset(in_bed), frozenset(set(by_id) - in_bed),
                        frozenset(holder_ids - in_bed), frozenset(in_bed - holder_ids))
    pairs = [] if hc else bed_pairs(beds, cap, present, holder_ids, asg)
    sev_total = sum(pp.severity for pp in pairs)
    if not hc and sev_total != sum(gap_b.values()):
        issues.append(_issue(day, "violation", "Critical", "pairing_closed_form_mismatch",
                             f"pairs {sev_total} vs closed form {sum(gap_b.values())}"))
    for pp in pairs:
        issues.append(_issue(day, "violation", "Major" if pp.severity >= 2 else "Moderate", f"bed_{pp.kind}",
                             {"unserved": pp.unserved_id, "unserved_department": pp.unserved_department,
                              "unserved_level": pp.unserved_level, "served": pp.served_id,
                              "served_department": pp.served_department, "served_level": pp.served_level,
                              "severity": pp.severity}))

    # ---- A3: floor per tier (policy-independent)
    floor_b = {}
    for j in LEVELS:
        nge = {d: sum(n[d][k] for k in LEVELS if k >= j) for d in DEPARTMENTS}
        floor_b[j] = sum(nge.values()) - min(P_B, sum(min(nge[d], cap) for d in DEPARTMENTS))
    raw_b = {j: sum(of[d][k] for d in DEPARTMENTS for k in LEVELS if k >= j) for j in LEVELS}

    # ---- nurses: own need, requirement, coverage C1 (hundredths)
    need = {d: {k: w[k] * n[d][k] for k in LEVELS} for d in DEPARTMENTS}
    req = {d: ceil_div(sum(need[d].values()), SCALE) for d in DEPARTMENTS}
    covered, shortage = {}, {}
    for d in DEPARTMENTS:
        rem = nurses[d] * SCALE
        covered[d] = {}
        for k in (3, 2, 1):
            covered[d][k] = min(need[d][k], max(0, rem))
            rem -= covered[d][k]
        shortage[d] = {k: need[d][k] - covered[d][k] for k in LEVELS}
    tier_a = {j: np.array([sum(need[d][k] for k in LEVELS if k >= j) for d in DEPARTMENTS]) for j in LEVELS}
    comp = compositions(P_N) * SCALE
    cov_all = {j: np.minimum(comp, tier_a[j][None, :]).sum(axis=1) for j in LEVELS}
    maxn = {j: int(cov_all[j].max()) for j in LEVELS}
    best = int(np.lexsort((cov_all[1], cov_all[2], cov_all[3]))[-1])        # lexicographic max (L3 first)
    lex_floor = {j: maxn[j] - int(cov_all[j][best]) for j in LEVELS}
    joint_floor = int(sum(maxn[j] - cov_all[j] for j in LEVELS).min())   # Log #47: reported, not used
    nv = np.array([nurses[d] * SCALE for d in DEPARTMENTS])
    gap_n = {j: maxn[j] - int(np.minimum(nv, tier_a[j]).sum()) for j in LEVELS}
    net_n = {j: gap_n[j] - lex_floor[j] for j in LEVELS}
    if not hc:
        top = next((j for j in (3, 2, 1) if net_n[j] > 0), None)
        if top is not None:
            issues.append(_issue(day, "violation", "Major" if top == 3 else "Moderate", "nurse_gap",
                                 {"net_gap_hundredths": net_n, "highest_tier": top}))

    # ---- B2: F1 inversions (normal days)
    inversions = []
    if not shock and not hc:
        room = {d: cap - beds[d] for d in DEPARTMENTS}
        admitted = [by_id[i] for i in in_bed - holder_ids]
        for k in LEVELS:
            waiting = sorted((p for p in present if p.patient_id not in in_bed and p.complexity == k),
                             key=lambda p: (p.arrival_day, int(p.patient_id[1:])))
            placed = sorted((p for p in admitted if p.complexity == k),
                            key=lambda p: (-p.arrival_day, -int(p.patient_id[1:])))
            used = [False] * len(placed)
            for p in waiting:
                if room[p.department] <= 0:
                    continue
                for i, q in enumerate(placed):
                    if not used[i] and q.department != p.department and q.arrival_day > p.arrival_day:
                        used[i] = True
                        room[p.department] -= 1
                        inversions.append({"level": k, "waiting": p.patient_id, "placed": q.patient_id,
                                           "days": q.arrival_day - p.arrival_day})
                        break
        for inv in inversions:
            issues.append(_issue(day, "concern", "Moderate", "f1_inversion", inv))

    # ---- stability reference: repair rule from the allocation in effect at t-1
    prev = rec.initial if day == 1 else rec.alloc[day - 1]
    ref = repair(prev["beds"], prev["nurses"], P_B, P_N, cap, holders, req)
    tau_b = {d: beds[d] - ref.beds[d] for d in DEPARTMENTS}
    tau_n = {d: nurses[d] - ref.nurses[d] for d in DEPARTMENTS}
    if not hc and (any(tau_b.values()) or any(tau_n.values())):
        same_beds = own_assignment(ref.beds, present, holder_ids) == in_bed
        same_nurses = True
        for d in DEPARTMENTS:
            rem = ref.nurses[d] * SCALE
            for k in (3, 2, 1):
                c = min(need[d][k], max(0, rem))
                rem -= c
                same_nurses &= (c == covered[d][k])
        if same_beds and same_nurses:
            issues.append(_issue(day, "improvement", "Minor", "reallocation_without_effect",
                                 {"tau_beds": tau_b, "tau_nurses": tau_n}))

    return {
        "day": day, "shock_day": shock, "hard_constraint_errors": hc, "replay_ok": replay_ok,
        "beds": beds, "nurses": nurses, "pool_beds": P_B, "pool_nurses": P_N, "source": a["source"],
        "census": n, "overflow": of, "occupied": occ, "in_bed_count": len(in_bed),
        "bed_max": max_b, "bed_achieved": ach_b, "bed_gap": gap_b, "bed_floor": floor_b, "bed_raw": raw_b,
        "pairs": [{"kind": pp.kind, "unserved_level": pp.unserved_level, "served_level": pp.served_level,
                   "severity": pp.severity} for pp in pairs],
        "need_h": need, "requirement": req, "covered_h": covered, "shortage_h": shortage,
        "nurse_max_h": maxn, "nurse_gap_h": gap_n, "nurse_lex_floor_h": lex_floor, "nurse_net_h": net_n,
        "nurse_joint_floor_h": joint_floor,
        "f1_inversions": inversions, "tau_beds": tau_b, "tau_nurses": tau_n,
        "in_bed": sorted(in_bed), "issues": issues,
    }


def audit_run(ds: Dataset, run_dir: Path) -> tuple[RunRecords, list[dict]]:
    rec = load_records(run_dir)
    w = weights_hundredths(ds.env)
    days = [audit_day(ds, rec, t, w) for t in range(1, ds.horizon + 1)]
    for x in rec.decisions:          # rejected submissions and failure days (agent runs only)
        if x.get("outcome") == "rejected":
            days[x["day"] - 1]["issues"].append(_issue(x["day"], "violation", "Moderate", "rejected_submission",
                                                       x.get("codes")))
    for t, dd in enumerate(days, 1):
        if dd["source"] == "repair_rule":
            dd["issues"].append(_issue(t, "violation", "Major", "allocator_failure_day", "repair rule applied"))
    return rec, days
