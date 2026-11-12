"""A tiny synthetic 5-day hospital for workflow tests and the smoke test (never a frozen dataset).

Hand-made, not drawn from the generator: no generation parameters are involved, and nothing an agent sees
in a smoke session says anything about the frozen data.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from src.utils.constants import DEPARTMENTS, LEVELS

DATASET_ID = "SMOKE5"
HORIZON = 5


def write_fixture(root: Path, seed: int = 0) -> Path:
    rng = random.Random(seed)
    root = Path(root)
    raw = root / "data" / "raw" / DATASET_ID
    meta = root / "data" / "metadata" / DATASET_ID
    raw.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    patients, num = [], 0
    for arrival in range(-3, HORIZON + 1):
        for d in DEPARTMENTS:
            for _ in range(rng.randint(0, 2) if arrival > 0 else 2):
                num += 1
                level = rng.choice(LEVELS)
                patients.append((f"P{num:06d}", d, level, arrival, arrival + rng.randint(2, 6)))
    pools = {t: (14 if t != 3 else 12, 5) for t in range(1, HORIZON + 1)}
    with open(raw / "patient_registry.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["patient_id", "department", "complexity", "arrival_day", "discharge_day"])
        w.writerows(patients)
    with open(raw / "hospital_resources_daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "total_beds", "total_nurses", "external_event"])
        for t, (b, n) in pools.items():
            prev = pools.get(t - 1)
            event = "" if prev is None or prev == (b, n) else f"bed pool {prev[0]} -> {b}"
            w.writerow([t, b, n, event])
    with open(raw / "department_demand_daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "department", "arrivals", "discharges", "census_L1", "census_L2", "census_L3"])
        for t in range(1, HORIZON + 1):
            for d in DEPARTMENTS:
                mine = [p for p in patients if p[1] == d]
                census = [sum(1 for p in mine if p[2] == k and p[3] <= t < p[4]) for k in LEVELS]
                w.writerow([t, d, sum(1 for p in mine if p[3] == t), sum(1 for p in mine if p[4] == t), *census])
    (meta / "environment_config.json").write_text(json.dumps({"max_beds": 5, "w_L1": 0.2, "w_L2": 0.35,
                                                              "w_L3": 0.6}, indent=2) + "\n", encoding="utf-8")
    return root
