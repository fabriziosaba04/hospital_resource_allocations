"""A harder synthetic 10-day hospital for the second dry run, DRY2 (owner decision §11 #41; Log #88).

Never a frozen dataset, and not derived from one: its own seed, its own parameters (below), its own simple
generator (Poisson arrivals, uniform integer lengths of stay), not `src/data_generation/`. The parameters are
chosen so that the fixture contains the situations the first fixture lacked (REFLECTION_LOG R29):

  - cross-department priority conflicts (an L3 or L2 patient waiting in a department with cap room while a
    movable bed in another department goes to an L1 patient, unless the allocation is changed);
  - same-level patients waiting in different departments (F1);
  - nurse rationing (N1 requirement above the nurse pool) on several days;
  - a forced shock cut (holders outnumber the bed pool);
  - pool increases and restores.

`tests/test_fixture_hard.py` asserts each of these. The parameters are written to the fixture's
`generation_config.json` (hidden, like the real one: no server tool reads it) and recorded in Log #88.
"""

from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

from src.utils.constants import DEPARTMENTS, LEVELS

DATASET_ID = "HARD10"
HORIZON = 10
SEED = 20261114

PARAMS = {
    "seed": SEED,
    "horizon": HORIZON,
    "burn_in_days": 6,
    "max_beds": 10,
    "weights": {"w_L1": 0.2, "w_L2": 0.35, "w_L3": 0.6},
    # arrivals per day (Poisson), and a cardiology surge
    "arrival_rate": {"internal_medicine": 2.0, "cardiology": 1.2, "neurology": 0.8, "orthopedics": 2.2},
    "surge": {"department": "cardiology", "days": [3, 7], "multiplier": 2.5},
    "complexity_mix": {"internal_medicine": [0.35, 0.45, 0.20], "cardiology": [0.10, 0.30, 0.60],
                       "neurology": [0.20, 0.40, 0.40], "orthopedics": [0.75, 0.20, 0.05]},
    # length of stay: uniform integer in [lo, hi] days, by level only
    "los": {"1": [1, 3], "2": [2, 5], "3": [4, 8]},
    # pools by day: increase on day 4, restore on day 6, forced cut on day 8, restore on day 10
    "bed_pool": {"1": 20, "2": 20, "3": 20, "4": 23, "5": 23, "6": 20, "7": 20, "8": 11, "9": 11, "10": 20},
    "nurse_pool": {"1": 6, "2": 6, "3": 6, "4": 8, "5": 8, "6": 6, "7": 6, "8": 5, "9": 5, "10": 6},
}


def _poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def patients(params: dict = PARAMS) -> list[tuple]:
    rng = random.Random(params["seed"])
    out, num = [], 0
    s = params["surge"]
    for arrival in range(1 - params["burn_in_days"], params["horizon"] + 1):
        for d in DEPARTMENTS:
            lam = params["arrival_rate"][d]
            if d == s["department"] and s["days"][0] <= arrival <= s["days"][1]:
                lam *= s["multiplier"]
            for _ in range(_poisson(rng, lam)):
                num += 1
                level = rng.choices(LEVELS, weights=params["complexity_mix"][d])[0]
                lo, hi = params["los"][str(level)]
                out.append((f"P{num:06d}", d, level, arrival, arrival + rng.randint(lo, hi)))
    return out


def _event(prev: tuple | None, cur: tuple) -> str:
    if prev is None or prev == cur:
        return ""
    parts = []
    if prev[0] != cur[0]:
        parts.append(f"bed pool {prev[0]} -> {cur[0]}")
    if prev[1] != cur[1]:
        parts.append(f"nurse pool {prev[1]} -> {cur[1]}")
    return "; ".join(parts)


def write_fixture(root: Path, params: dict = PARAMS) -> Path:
    root = Path(root)
    raw = root / "data" / "raw" / DATASET_ID
    meta = root / "data" / "metadata" / DATASET_ID
    raw.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    pts = patients(params)
    H = params["horizon"]
    pools = {t: (params["bed_pool"][str(t)], params["nurse_pool"][str(t)]) for t in range(1, H + 1)}
    with open(raw / "patient_registry.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["patient_id", "department", "complexity", "arrival_day", "discharge_day"])
        w.writerows(pts)
    with open(raw / "hospital_resources_daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "total_beds", "total_nurses", "external_event"])
        for t, (b, n) in pools.items():
            w.writerow([t, b, n, _event(pools.get(t - 1), (b, n))])
    with open(raw / "department_demand_daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "department", "arrivals", "discharges", "census_L1", "census_L2", "census_L3"])
        for t in range(1, H + 1):
            for d in DEPARTMENTS:
                mine = [p for p in pts if p[1] == d]
                census = [sum(1 for p in mine if p[2] == k and p[3] <= t < p[4]) for k in LEVELS]
                w.writerow([t, d, sum(1 for p in mine if p[3] == t), sum(1 for p in mine if p[4] == t), *census])
    (meta / "environment_config.json").write_text(json.dumps({"max_beds": params["max_beds"],
                                                              **params["weights"]}, indent=2) + "\n",
                                                  encoding="utf-8")
    (meta / "generation_config.json").write_text(json.dumps(params, indent=2) + "\n", encoding="utf-8")
    return root
