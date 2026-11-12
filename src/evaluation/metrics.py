"""Run metrics from the per-day audit (EVALUATION_PLAN.md §3), and the audit record files (PROJECT_SPEC.md §4)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.utils.constants import DEPARTMENTS, LEVELS

from .audit import SCALE, audit_run
from .dataset import ROOT, Dataset

WINDOWS = (2, 3, 5)          # W = 3 headline; 2 and 5 pre-registered sensitivity checks (§11 #19)
LEVEL_ORDER = ("Critical", "Major", "Moderate", "Minor")


def reversal_matches(series: list[int], window: int) -> list[tuple[int, int, int, int]]:
    """Units of one sign matched with later units of the opposite sign within `window` days, oldest first.
    Returns (t1, t2, units, sign of the first move)."""
    pos: list[list[int]] = []     # [day, units] unmatched gains
    neg: list[list[int]] = []
    out = []
    for t, x in enumerate(series, 1):
        for q in (pos, neg):
            q[:] = [e for e in q if t - e[0] <= window]
        if x == 0:
            continue
        opp, own = (neg, pos) if x > 0 else (pos, neg)
        left = abs(x)
        for e in opp:
            if left == 0:
                break
            m = min(left, e[1])
            e[1] -= m
            left -= m
            out.append((e[0], t, m, -1 if x > 0 else 1))
        opp[:] = [e for e in opp if e[1] > 0]
        if left:
            own.append([t, left])
    return out


def reversals(series: list[int], window: int) -> int:
    """All reversals: matched units, both directions (EVALUATION_PLAN.md §3.8)."""
    return sum(m[2] for m in reversal_matches(series, window))


def _h(x: int) -> float:
    return round(x / SCALE, 4)


def compute_metrics(ds: Dataset, days: list[dict]) -> dict:
    H = len(days)
    m: dict = {"dataset_id": ds.dataset_id, "horizon": H}

    # gate D
    m["D"] = {"hard_constraint_violations_in_effect": sum(len(d["hard_constraint_errors"]) for d in days),
              "replay_mismatches": sum(not d["replay_ok"] for d in days),
              "failure_days": sum(d["source"] == "repair_rule" for d in days),
              "rejected_submissions": sum(1 for d in days for i in d["issues"] if i["type"] == "rejected_submission"),
              "pairing_closed_form_mismatches": sum(1 for d in days for i in d["issues"]
                                                    if i["type"] == "pairing_closed_form_mismatch")}
    m["D"]["gate_passed"] = (m["D"]["hard_constraint_violations_in_effect"] == 0 and m["D"]["replay_mismatches"] == 0
                             and m["D"]["pairing_closed_form_mismatches"] == 0)

    # A1
    pairs = [p for d in days for p in d["pairs"]]
    by_kind = {k: {"pairs": sum(1 for p in pairs if p["kind"] == k),
                   "severity": sum(p["severity"] for p in pairs if p["kind"] == k)}
               for k in ("displaced", "empty", "shock_cut")}
    m["A1"] = {"SV_B": sum(sum(d["bed_gap"].values()) for d in days), "by_type": by_kind,
               "by_tier": {j: sum(d["bed_gap"][j] for d in days) for j in LEVELS},
               "severity_distribution": dict(sorted(Counter(p["severity"] for p in pairs).items()))}

    # A2
    m["A2"] = {f"tier{j}": {"raw_gap": _h(sum(d["nurse_gap_h"][j] for d in days)),
                            "lex_floor": _h(sum(d["nurse_lex_floor_h"][j] for d in days)),
                            "SV_N": _h(sum(d["nurse_net_h"][j] for d in days))} for j in (3, 2, 1)}
    m["A2"]["days_lex_floor_ne_joint_floor"] = sum(sum(d["nurse_lex_floor_h"].values()) != d["nurse_joint_floor_h"]
                                                   for d in days)

    # A3
    a3 = {}
    for j in LEVELS:
        raw = sum(d["bed_raw"][j] for d in days)
        floor = sum(d["bed_floor"][j] for d in days)
        avoid = sum(d["bed_gap"][j] for d in days)
        path_daily = [d["bed_raw"][j] - d["bed_floor"][j] - d["bed_gap"][j] for d in days]
        a3[f"tier{j}"] = {"raw": raw, "floor": floor, "excess": raw - floor, "avoid": avoid,
                          "path": raw - floor - avoid, "min_daily_path": min(path_daily)}
    m["A3"] = a3

    # A4
    m["A4"] = {"shortage_by_level": {k: _h(sum(d["shortage_h"][dp][k] for d in days for dp in DEPARTMENTS))
                                     for k in LEVELS},
               "tier_floor": {j: _h(sum(sum(d["need_h"][dp][k] for dp in DEPARTMENTS for k in LEVELS if k >= j)
                                        - d["nurse_max_h"][j] for d in days)) for j in LEVELS}}

    # B1 overflow-rate dispersion, net of cap excess (lowest levels of the overflow first)
    of_net = {dp: {k: 0 for k in LEVELS} for dp in DEPARTMENTS}
    n_sum = {dp: {k: 0 for k in LEVELS} for dp in DEPARTMENTS}
    for d in days:
        for dp in DEPARTMENTS:
            cnt = d["census"][dp]
            capex = max(0, sum(cnt.values()) - ds.max_beds)
            for k in LEVELS:
                take = min(d["overflow"][dp][k], capex)
                capex -= take
                of_net[dp][k] += d["overflow"][dp][k] - take
                n_sum[dp][k] += cnt[k]
    b1 = {}
    for k in LEVELS:
        rates = {dp: of_net[dp][k] / n_sum[dp][k] for dp in DEPARTMENTS if n_sum[dp][k] > 0}
        b1[f"L{k}"] = {"dispersion_pp": round(100 * (max(rates.values()) - min(rates.values())), 2),
                       "rates_pct": {dp: round(100 * r, 2) for dp, r in rates.items()},
                       "denominators": {dp: n_sum[dp][k] for dp in DEPARTMENTS}}
    m["B1"] = b1

    # B2 F1 inversions
    inv = [x for d in days for x in d["f1_inversions"]]
    m["B2"] = {f"L{k}": {"count": sum(1 for x in inv if x["level"] == k),
                         "wait_days": sum(x["days"] for x in inv if x["level"] == k)} for k in LEVELS}

    # B3 wait distribution
    lvl = {}
    ovf_days: Counter = Counter()
    for d in days:
        in_bed = set(d["in_bed"])
        for p in ds.present(d["day"]):
            lvl[p.patient_id] = p.complexity
            if p.patient_id not in in_bed:
                ovf_days[p.patient_id] += 1
    m["B3"] = {}
    for k in LEVELS:
        v = [c for pid, c in ovf_days.items() if lvl[pid] == k]
        m["B3"][f"L{k}"] = {"patients_ever_in_overflow": len(v),
                            "mean_days": round(sum(v) / len(v), 3) if v else 0.0, "max_days": max(v, default=0)}

    # B4
    b4 = {}
    for k in LEVELS:
        rc = {}
        for dp in DEPARTMENTS:
            nd = sum(d["need_h"][dp][k] for d in days)
            if nd > 0:
                rc[dp] = sum(d["covered_h"][dp][k] for d in days) / nd
        b4[f"L{k}"] = {"dispersion": round(max(rc.values()) - min(rc.values()), 4),
                       "coverage": {dp: round(r, 4) for dp, r in rc.items()}}
    m["B4"] = b4

    # C
    m["C"] = {"C1_bed_utilisation": round(sum(d["in_bed_count"] for d in days) / sum(d["pool_beds"] for d in days), 4),
              "C2_avoidable_idle_bed_days": by_kind["empty"]["pairs"],
              "C3_nurse_utilisation": round(sum(min(d["nurses"][dp], d["requirement"][dp]) for d in days
                                                for dp in DEPARTMENTS) / sum(d["pool_nurses"] for d in days), 4),
              "C4_avoidable_idle_nurse_days": sum(min(sum(max(0, d["nurses"][dp] - d["requirement"][dp]) for dp in DEPARTMENTS),
                                                      sum(max(0, d["requirement"][dp] - d["nurses"][dp]) for dp in DEPARTMENTS))
                                                  for d in days),
              "C4_unavoidable_idle_nurse_days": sum(max(0, d["pool_nurses"] - sum(d["requirement"].values())) for d in days)}

    # E
    e = {}
    for res, key in (("beds", "tau_beds"), ("nurses", "tau_nurses")):
        rs = [sum(abs(v) for v in d[key].values()) / 2 for d in days]
        e[res] = {"RS_total": sum(rs), "frequency_days": sum(1 for x in rs if x > 0),
                  "reversals": {f"W{w}": sum(reversals([d[key][dp] for d in days], w) for dp in DEPARTMENTS)
                                for w in WINDOWS}}
    m["E"] = e

    # issues by level (reversal issues are added per day in build_issue_list)
    m["issues_by_level"] = {lv: 0 for lv in LEVEL_ORDER}
    for d in days:
        for i in d["issues"]:
            m["issues_by_level"][i["level"]] += 1
    return m


def add_reversal_issues(days: list[dict], window: int = 3) -> None:
    """Minor concern on day t2 for each unit reversed within W (EVALUATION_PLAN.md §4)."""
    for res, key in (("beds", "tau_beds"), ("nurses", "tau_nurses")):
        for dp in DEPARTMENTS:
            series = [d[key][dp] for d in days]
            before = 0
            for t in range(1, len(series) + 1):
                now = reversals(series[:t], window)
                if now > before:
                    days[t - 1]["issues"].append({"day": t, "category": "concern", "level": "Minor",
                                                  "type": f"{res}_reversal",
                                                  "detail": {"department": dp, "units": now - before, "window": window}})
                before = now


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def evaluate_run(ds: Dataset, run_dir: Path, out_root: Path = ROOT / "results" / "evaluations") -> dict:
    rec, days = audit_run(ds, run_dir)
    add_reversal_issues(days)
    metrics = compute_metrics(ds, days)
    metrics["run_id"] = rec.run_id
    out = out_root / rec.run_id
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = []
    for start in range(1, len(days) + 1, 5):          # one record per five-day audit period
        period = days[start - 1: start + 4]
        lines.append({"run_id": rec.run_id, "day": period[-1]["day"], "writer": "deterministic_audit",
                      "created_at": now, "inputs": {"dataset_id": ds.dataset_id},
                      "period": {"from_day": period[0]["day"], "to_day": period[-1]["day"]},
                      "days": [{k: v for k, v in d.items() if k != "in_bed"} for d in period]})
    (out / "deterministic_audit.jsonl").write_text("".join(json.dumps(_jsonable(x), sort_keys=True) + "\n"
                                                           for x in lines), encoding="utf-8", newline="\n")
    (out / "metrics.json").write_text(json.dumps(_jsonable(metrics), indent=2, sort_keys=True) + "\n",
                                      encoding="utf-8", newline="\n")
    return metrics
