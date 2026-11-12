"""ANALYZER (AGENTS.md §4): deterministic `run_analyzer`, writing the Observed State for day t.

Facts only, no thresholds and no recommendations (Decisions Log #61). It reads the demand and pool rows up
to day t, and occupied beds O_d(t) from the previous Bed Assignment State. It never reads
`generation_config` and never exposes a discharge day.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.environment.nurses import requirement as n1_requirement
from src.utils.constants import DEPARTMENTS, LEVELS


def read_tables_up_to(data_root: Path, dataset_id: str, day: int) -> tuple[dict, dict]:
    raw = Path(data_root) / "data" / "raw" / dataset_id
    pools, demand = {}, {}
    with open(raw / "hospital_resources_daily.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = int(r["day"])
            if t <= day:
                pools[t] = {"beds": int(r["total_beds"]), "nurses": int(r["total_nurses"]),
                            "external_event": r["external_event"]}
    with open(raw / "department_demand_daily.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = int(r["day"])
            if t <= day:
                demand[(t, r["department"])] = {"arrivals": int(r["arrivals"]), "discharges": int(r["discharges"]),
                                                "census": {k: int(r[f"census_L{k}"]) for k in LEVELS}}
    return pools, demand


def _mean(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def run_analyzer(data_root: Path, dataset_id: str, day: int, env: dict, occupied: dict[str, int],
                 allocation_in_effect: dict, previous_overflow: dict[str, dict[int, int]] | None) -> dict:
    pools, demand = read_tables_up_to(data_root, dataset_id, day)
    p, prev = pools[day], pools.get(day - 1)
    external = {
        "beds_change": None if prev is None else p["beds"] - prev["beds"],
        "nurses_change": None if prev is None else p["nurses"] - prev["nurses"],
        "external_event": p["external_event"],
        "note": "hospital-level pool changes only; never caused by the ALLOCATOR",
    }
    depts = {}
    for d in DEPARTMENTS:
        today = demand[(day, d)]
        yday = demand.get((day - 1, d))
        arrivals_hist = [demand[(t, d)]["arrivals"] for t in range(1, day + 1) if (t, d) in demand]
        census_total = sum(today["census"].values())
        c = today["census"]
        depts[d] = {
            "arrivals": today["arrivals"], "discharges": today["discharges"],
            "census_by_level": {str(k): c[k] for k in LEVELS}, "census_total": census_total,
            "census_change": None if yday is None else census_total - sum(yday["census"].values()),
            "occupied_beds": occupied[d],
            "nurse_requirement_N1": n1_requirement(c[1], c[2], c[3], env),
            "arrivals_mean_last_3_days": _mean(arrivals_hist[-3:]),
            "arrivals_mean_last_7_days": _mean(arrivals_hist[-7:]),
            "arrivals_mean_all_days": _mean(arrivals_hist),
            "overflow_yesterday_by_level": None if previous_overflow is None
            else {str(k): previous_overflow[d][k] for k in LEVELS},
        }
    beds_alloc, nurses_alloc = allocation_in_effect["beds"], allocation_in_effect["nurses"]
    total_occ = sum(occupied.values())
    feasibility = {
        "beds_allocated_vs_pool": sum(beds_alloc.values()) - p["beds"],
        "nurses_allocated_vs_pool": sum(nurses_alloc.values()) - p["nurses"],
        "occupied_beds_total": total_occ,
        "shock_shortfall": max(0, total_occ - p["beds"]),
        "current_allocation_feasible_today": sum(beds_alloc.values()) == p["beds"]
        and sum(nurses_alloc.values()) == p["nurses"] and total_occ <= p["beds"]
        and all(beds_alloc[d] >= occupied[d] for d in DEPARTMENTS),
    }
    imbalance = {d: {"beds_allocated_minus_census": beds_alloc[d] - depts[d]["census_total"],
                     "nurses_allocated_minus_requirement": nurses_alloc[d] - depts[d]["nurse_requirement_N1"]}
                 for d in DEPARTMENTS}
    return {"pools": {"beds": p["beds"], "nurses": p["nurses"]}, "external_changes": external,
            "departments": depts, "feasibility_of_current_allocation": feasibility,
            "allocation_vs_demand": imbalance, "max_beds": env["max_beds"],
            "nurse_weights": {f"L{k}": env[f"w_L{k}"] for k in LEVELS}}
