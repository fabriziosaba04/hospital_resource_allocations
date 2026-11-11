"""Descriptive statistics of a generated dataset (used for the generation report and the Monte Carlo)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.utils.constants import DEPARTMENTS

CENSUS_COLS = ["census_L1", "census_L2", "census_L3"]


def weights_hundredths(env: dict) -> tuple[int, int, int]:
    """Nurse weights as exact integers in hundredths, so that ceil() has no floating-point error."""
    w = tuple(int(round(env[k] * 100)) for k in ("w_L1", "w_L2", "w_L3"))
    for k, wi in zip(("w_L1", "w_L2", "w_L3"), w):
        if abs(env[k] * 100 - wi) > 1e-9:
            raise ValueError(f"{k} is not a multiple of 0.01")
    return w


def n1_requirement(n1, n2, n3, env: dict):
    """N1: ceil(sum_p w(level_p)), computed in exact integer arithmetic."""
    w1, w2, w3 = weights_hundredths(env)
    s = w1 * np.asarray(n1) + w2 * np.asarray(n2) + w3 * np.asarray(n3)
    return -(-s // 100)


def typed(data: dict) -> dict:
    """Convert string-typed frames loaded from CSV to integer columns."""
    out = dict(data)
    out["resources"] = data["resources"].astype({"day": int, "total_beds": int, "total_nurses": int})
    out["demand"] = data["demand"].astype({c: int for c in ["day", "arrivals", "discharges", *CENSUS_COLS]})
    out["registry"] = data["registry"].astype({"complexity": int, "arrival_day": int, "discharge_day": int})
    return out


def compute_stats(resources: pd.DataFrame, demand: pd.DataFrame, registry: pd.DataFrame, env: dict) -> dict:
    d = demand.copy()
    d["census"] = d[CENSUS_COLS].sum(axis=1)
    d["n1_req"] = n1_requirement(d["census_L1"], d["census_L2"], d["census_L3"], env)
    by_day = d.groupby("day").agg(census=("census", "sum"), n1_req=("n1_req", "sum"),
                                 L1=("census_L1", "sum"), L2=("census_L2", "sum"), L3=("census_L3", "sum"))
    res = resources.set_index("day")
    by_day = by_day.join(res[["total_beds", "total_nurses"]])
    over_beds = by_day[by_day["census"] > by_day["total_beds"]]
    over_nurses = by_day[by_day["n1_req"] > by_day["total_nurses"]]
    max_beds = int(env["max_beds"])
    dept_over_cap = d[d["census"] > max_beds]

    out = {
        "census_total": {
            "mean": float(by_day["census"].mean()),
            "min": int(by_day["census"].min()),
            "max": int(by_day["census"].max()),
            "day1": int(by_day["census"].iloc[0]),
        },
        "census_by_level_mean": {f"L{k}": float(by_day[f"L{k}"].mean()) for k in (1, 2, 3)},
        "census_by_department": {
            dept: {
                "mean": float(s.mean()), "min": int(s.min()), "max": int(s.max()),
            }
            for dept in DEPARTMENTS
            for s in [d.loc[d["department"] == dept, "census"]]
        },
        "mean_occupancy_census_over_beds": float((by_day["census"] / by_day["total_beds"]).mean()),
        "days_census_gt_total_beds": {
            "count": int(len(over_beds)),
            "days": [int(x) for x in over_beds.index],
            "total_excess_patient_days": int((over_beds["census"] - over_beds["total_beds"]).sum()),
            "max_excess": int((over_beds["census"] - over_beds["total_beds"]).max()) if len(over_beds) else 0,
        },
        "department_days_census_gt_max_beds": {
            "count": int(len(dept_over_cap)),
            "cases": [f"day {r.day} {r.department} ({r.census})" for r in dept_over_cap.itertuples()],
        },
        "n1_requirement": {
            "mean": float(by_day["n1_req"].mean()),
            "min": int(by_day["n1_req"].min()),
            "max": int(by_day["n1_req"].max()),
            "mean_total_nurses": float(by_day["total_nurses"].mean()),
            "mean_ratio_nurses_over_requirement": float((by_day["total_nurses"] / by_day["n1_req"]).mean()),
            "days_requirement_gt_nurses": int(len(over_nurses)),
            "days_requirement_gt_nurses_list": [int(x) for x in over_nurses.index],
            "total_shortage_nurse_days": int((over_nurses["n1_req"] - over_nurses["total_nurses"]).sum()),
            "max_shortage": int((over_nurses["n1_req"] - over_nurses["total_nurses"]).max()) if len(over_nurses) else 0,
        },
        "arrivals_horizon_by_department_mean_per_day": {
            dept: float(d.loc[d["department"] == dept, "arrivals"].mean()) for dept in DEPARTMENTS
        },
        "cardiology_arrivals_mean_surge_days_12_19": float(
            d.loc[(d["department"] == "cardiology") & d["day"].between(12, 19), "arrivals"].mean()
        ),
        "n_patients": {
            "total": int(len(registry)),
            "burn_in": int((registry["arrival_day"] <= 0).sum()),
            "horizon": int((registry["arrival_day"] >= 1).sum()),
        },
    }
    los = registry["discharge_day"] - registry["arrival_day"]
    out["los_by_level"] = {}
    for k in (1, 2, 3):
        s = los[registry["complexity"] == k]
        out["los_by_level"][f"L{k}"] = {
            "n": int(len(s)), "mean": float(s.mean()), "cv": float(s.std(ddof=1) / s.mean()),
            "min": int(s.min()), "max": int(s.max()),
        }
    out["daily"] = {
        "census": by_day["census"].astype(int).tolist(),
        "total_beds": by_day["total_beds"].astype(int).tolist(),
        "n1_req": by_day["n1_req"].astype(int).tolist(),
        "total_nurses": by_day["total_nurses"].astype(int).tolist(),
    }
    return out


def scalar_metrics(stats: dict) -> dict[str, float]:
    """Flat scalar view used for Monte Carlo comparison."""
    m = {
        "census_total_mean": stats["census_total"]["mean"],
        "census_total_min": stats["census_total"]["min"],
        "census_total_max (surge peak)": stats["census_total"]["max"],
        "census_day1": stats["census_total"]["day1"],
        "days_census_gt_total_beds": stats["days_census_gt_total_beds"]["count"],
        "excess_patient_days_over_total_beds": stats["days_census_gt_total_beds"]["total_excess_patient_days"],
        "dept_days_census_gt_max_beds": stats["department_days_census_gt_max_beds"]["count"],
        "n1_requirement_mean": stats["n1_requirement"]["mean"],
        "n1_requirement_max": stats["n1_requirement"]["max"],
        "days_n1_gt_total_nurses": stats["n1_requirement"]["days_requirement_gt_nurses"],
    }
    for dept, s in stats["census_by_department"].items():
        m[f"census_{dept}_mean"] = s["mean"]
        m[f"census_{dept}_max"] = s["max"]
    for k, s in stats["los_by_level"].items():
        m[f"los_{k}_mean"] = s["mean"]
        m[f"los_{k}_cv"] = s["cv"]
    return m
