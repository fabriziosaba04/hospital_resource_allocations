"""Stochastic hospital data generator (PROJECT_SPEC.md §7, DATA_DICTIONARY.md §3).

Days -burn_in+1 ... H are simulated in within-day order: discharges, then arrivals.
`department_demand_daily` is written from running counters maintained during the simulation,
never by querying the registry, so that reconciliation (DATA_DICTIONARY.md §4.1) is a genuine check.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.constants import DEPARTMENTS, LEVELS

from .los import calibrate

RESOURCES_COLUMNS = ["day", "total_beds", "total_nurses", "external_event"]
DEMAND_COLUMNS = ["day", "department", "arrivals", "discharges", "census_L1", "census_L2", "census_L3"]
REGISTRY_COLUMNS = ["patient_id", "department", "complexity", "arrival_day", "discharge_day"]


@dataclass
class GeneratedDataset:
    dataset_id: str
    seed: int
    resources: pd.DataFrame
    demand: pd.DataFrame
    registry: pd.DataFrame
    generation_config: dict
    environment_config: dict


def dataset_id_for(seed: int) -> str:
    return f"seed{seed}"


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def arrival_rate(cfg: dict, department: str, day: int) -> float:
    rate = float(cfg["arrival_rates"][department])
    for surge in cfg.get("surges", []):
        if surge["department"] == department and surge["from_day"] <= day <= surge["to_day"]:
            rate *= float(surge["multiplier"])
    return rate


def pools_for_day(cfg: dict, day: int) -> tuple[int, int]:
    beds = int(cfg["base_pools"]["total_beds"])
    nurses = int(cfg["base_pools"]["total_nurses"])
    for shock in cfg.get("shocks", []):
        if shock["from_day"] <= day <= shock["to_day"]:
            if shock["resource"] == "beds":
                beds += int(shock["delta"])
            elif shock["resource"] == "nurses":
                nurses += int(shock["delta"])
            else:
                raise ValueError(f"unknown shock resource {shock['resource']!r}")
    return beds, nurses


def _change_text(pool: str, delta: int) -> str:
    return f"{pool} pool {'increased' if delta > 0 else 'reduced'} by {abs(delta)}"


def external_event(prev: tuple[int, int] | None, cur: tuple[int, int]) -> str:
    """Current-day change only, relative to the previous day (approved 2026-11-07 and 2026-11-11).

    Empty on day 1 and on every day the pools do not change. No duration or forecast is stated.
    """
    if prev is None:
        return ""
    parts = []
    if cur[0] != prev[0]:
        parts.append(_change_text("bed", cur[0] - prev[0]))
    if cur[1] != prev[1]:
        parts.append(_change_text("nurse", cur[1] - prev[1]))
    return "; ".join(parts)


def generate(gen_cfg: dict, env_cfg: dict, seed: int, dataset_id: str | None = None) -> GeneratedDataset:
    """`dataset_id` defaults to seed<seed>; a labelled variant (e.g. a stress case) passes its own."""
    dataset_id = dataset_id or dataset_id_for(seed)
    horizon = int(gen_cfg["horizon_days"])
    burn_in = int(gen_cfg["burn_in_days"])
    los_cfg = gen_cfg["length_of_stay"]
    if los_cfg["distribution"] != "discretised_lognormal_ceiling":
        raise ValueError("only discretised_lognormal_ceiling is supported")
    cal = calibrate(float(los_cfg["cv_continuous"]), {int(k): v for k, v in los_cfg["discrete_means"].items()})
    sigma = cal["sigma"]
    mu_by_level = np.array([cal["mu"][lv] for lv in LEVELS])

    rng = np.random.default_rng(seed)
    n_dept, n_lvl = len(DEPARTMENTS), len(LEVELS)

    census = np.zeros((n_dept, n_lvl), dtype=np.int64)          # running counter
    scheduled: dict[int, np.ndarray] = {}                         # discharge day -> counts
    reg_dept, reg_lvl, reg_arr, reg_dis = [], [], [], []
    demand_rows = []

    for day in range(1 - burn_in, horizon + 1):
        # 1. discharges (bed is free on the discharge day)
        discharged = scheduled.pop(day, np.zeros((n_dept, n_lvl), dtype=np.int64))
        census -= discharged
        # 2. arrivals, departments in fixed order
        arrived = np.zeros((n_dept, n_lvl), dtype=np.int64)
        for i, dept in enumerate(DEPARTMENTS):
            n = int(rng.poisson(arrival_rate(gen_cfg, dept, day)))
            if n == 0:
                continue
            levels = rng.choice(np.array(LEVELS), size=n, p=gen_cfg["complexity_mix"][dept])
            z = rng.standard_normal(n)
            los = np.maximum(1, np.ceil(np.exp(mu_by_level[levels - 1] + sigma * z))).astype(np.int64)
            for lv, stay in zip(levels.tolist(), los.tolist()):
                reg_dept.append(dept)
                reg_lvl.append(lv)
                reg_arr.append(day)
                reg_dis.append(day + stay)
                arrived[i, lv - 1] += 1
                sched = scheduled.setdefault(day + stay, np.zeros((n_dept, n_lvl), dtype=np.int64))
                sched[i, lv - 1] += 1
        census += arrived
        if (census < 0).any():  # cannot happen; guards the counter logic
            raise RuntimeError(f"negative census on day {day}")
        if day >= 1:
            for i, dept in enumerate(DEPARTMENTS):
                demand_rows.append(
                    [day, dept, int(arrived[i].sum()), int(discharged[i].sum()), *map(int, census[i])]
                )

    registry = pd.DataFrame(
        {
            "patient_id": [f"P{k:06d}" for k in range(1, len(reg_dept) + 1)],
            "department": reg_dept,
            "complexity": reg_lvl,
            "arrival_day": reg_arr,
            "discharge_day": reg_dis,
        },
        columns=REGISTRY_COLUMNS,
    )
    if len(registry) > 999_999:
        raise RuntimeError("patient_id space exhausted")

    res_rows, prev = [], None
    for day in range(1, horizon + 1):
        cur = pools_for_day(gen_cfg, day)
        res_rows.append([day, cur[0], cur[1], external_event(prev, cur)])
        prev = cur
    resources = pd.DataFrame(res_rows, columns=RESOURCES_COLUMNS)
    demand = pd.DataFrame(demand_rows, columns=DEMAND_COLUMNS)

    written_cfg = copy.deepcopy(gen_cfg)
    written_cfg["seed"] = seed
    written_cfg["dataset_id"] = dataset_id
    written_cfg["length_of_stay"]["calibration"] = {
        "sigma": sigma,
        "mu": {str(k): v for k, v in cal["mu"].items()},
        "theoretical_discrete_mean": {str(k): v for k, v in cal["discrete_mean"].items()},
        "theoretical_discrete_cv": {str(k): v for k, v in cal["discrete_cv"].items()},
    }
    written_cfg["rng"] = "numpy.random.default_rng(seed); draws per day, then department in fixed order: Poisson count, complexities, standard normals for LOS"

    return GeneratedDataset(
        dataset_id=dataset_id,
        seed=seed,
        resources=resources,
        demand=demand,
        registry=registry,
        generation_config=written_cfg,
        environment_config=copy.deepcopy(env_cfg),
    )


def dataset_paths(root: str | Path, dataset_id: str) -> dict[str, Path]:
    root = Path(root)
    raw = root / "data" / "raw" / dataset_id
    meta = root / "data" / "metadata" / dataset_id
    return {
        "raw": raw,
        "meta": meta,
        "processed": root / "data" / "processed" / dataset_id,
        "resources": raw / "hospital_resources_daily.csv",
        "demand": raw / "department_demand_daily.csv",
        "registry": raw / "patient_registry.csv",
        "environment_config": meta / "environment_config.json",
        "generation_config": meta / "generation_config.json",
        "validation_report": root / "data" / "processed" / dataset_id / "validation_report.json",
    }


def write_dataset(ds: GeneratedDataset, root: str | Path, overwrite: bool = False) -> dict[str, Path]:
    paths = dataset_paths(root, ds.dataset_id)
    if paths["raw"].exists() and not overwrite:
        raise FileExistsError(f"{paths['raw']} already exists; original datasets are immutable (use --overwrite deliberately)")
    for key in ("raw", "meta", "processed"):
        paths[key].mkdir(parents=True, exist_ok=True)
    ds.resources.to_csv(paths["resources"], index=False, lineterminator="\n")
    ds.demand.to_csv(paths["demand"], index=False, lineterminator="\n")
    ds.registry.to_csv(paths["registry"], index=False, lineterminator="\n")
    for key, obj in (("environment_config", ds.environment_config), ("generation_config", ds.generation_config)):
        with open(paths[key], "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")
    return paths

