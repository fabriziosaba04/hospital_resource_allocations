"""Dataset validation and reconciliation checks (DATA_DICTIONARY.md §4).

This module is deliberately independent of the generator: it reads the written files from disk,
recomputes every expected quantity from the registry with its own code, and never imports
generator logic. It does not depend on any LLM output.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from src.utils.constants import DEPARTMENTS, LEVELS

SCHEMA = {
    "resources": ["day", "total_beds", "total_nurses", "external_event"],
    "demand": ["day", "department", "arrivals", "discharges", "census_L1", "census_L2", "census_L3"],
    "registry": ["patient_id", "department", "complexity", "arrival_day", "discharge_day"],
}
CENSUS_COLS = ["census_L1", "census_L2", "census_L3"]
ID_RE = re.compile(r"^P\d{6}$")
MAX_EXAMPLES = 5


@dataclass
class CheckResult:
    check_id: str
    section: str
    description: str
    passed: bool
    n_failures: int = 0
    examples: list[str] = field(default_factory=list)


def _fail_list(check_id, section, description, failures: list[str]) -> CheckResult:
    return CheckResult(check_id, section, description, not failures, len(failures), failures[:MAX_EXAMPLES])


# ----------------------------------------------------------------------------- loading

def load_dataset(root: str | Path, dataset_id: str) -> dict:
    root = Path(root)
    raw = root / "data" / "raw" / dataset_id
    meta = root / "data" / "metadata" / dataset_id
    read = lambda name: pd.read_csv(raw / name, keep_default_na=False, dtype=str)  # noqa: E731
    with open(meta / "environment_config.json", encoding="utf-8") as fh:
        env = json.load(fh)
    with open(meta / "generation_config.json", encoding="utf-8") as fh:
        gen = json.load(fh)
    return {
        "resources": read("hospital_resources_daily.csv"),
        "demand": read("department_demand_daily.csv"),
        "registry": read("patient_registry.csv"),
        "environment_config": env,
        "generation_config": gen,
    }


def _int_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="raise").astype("int64")
    return out


# ----------------------------------------------------------------------------- schema and types

def check_schema(data) -> CheckResult:
    failures = [
        f"{name}: columns {list(data[name].columns)} != {cols}"
        for name, cols in SCHEMA.items()
        if list(data[name].columns) != cols
    ]
    return _fail_list("I0_schema", "4.2", "Every table has exactly the documented columns, in order", failures)


def _non_negative_int_failures(df: pd.DataFrame, table: str, cols: list[str], allow_negative=()) -> list[str]:
    failures = []
    for c in cols:
        for idx, v in df[c].items():
            s = str(v).strip()
            if not re.fullmatch(r"-?\d+", s):
                failures.append(f"{table} row {idx}: {c}={v!r} is not an integer")
            elif c not in allow_negative and int(s) < 0:
                failures.append(f"{table} row {idx}: {c}={v!r} is negative")
    return failures


def check_integer_fields(data) -> CheckResult:
    f = _non_negative_int_failures(data["demand"], "demand", ["day", "arrivals", "discharges", *CENSUS_COLS])
    f += _non_negative_int_failures(
        data["registry"], "registry", ["complexity", "arrival_day", "discharge_day"],
        allow_negative=("arrival_day", "discharge_day"),
    )
    f += _non_negative_int_failures(data["resources"], "resources", ["day"])
    return _fail_list("I8_integer_fields", "3", "Count, day and complexity fields are integers; counts are non-negative", f)


# ----------------------------------------------------------------------------- 4.2 integrity

def check_unique_ids(data) -> CheckResult:
    ids = data["registry"]["patient_id"]
    dup = ids[ids.duplicated(keep=False)].unique().tolist()
    return _fail_list("I1_unique_patient_id", "4.2", "patient_id is unique", [f"duplicate {d}" for d in dup])


def check_id_format_and_order(data) -> CheckResult:
    reg = data["registry"]
    failures = [f"bad patient_id {p!r}" for p in reg["patient_id"] if not ID_RE.match(str(p))]
    if not failures:
        r = _int_frame(reg, ["arrival_day"]).sort_values("patient_id")
        arr = r["arrival_day"].to_numpy()
        ids = r["patient_id"].to_numpy()
        failures += [
            f"{ids[i]} (arrival {arr[i]}) precedes {ids[i + 1]} (arrival {arr[i + 1]})"
            for i in range(len(arr) - 1)
            if arr[i] > arr[i + 1]
        ]
    return _fail_list("I1b_patient_id_format_order", "3.3",
                      "patient_id is P + six digits, and ID order matches arrival order", failures)


def check_discharge_after_arrival(data) -> CheckResult:
    r = _int_frame(data["registry"], ["arrival_day", "discharge_day"])
    bad = r[r["discharge_day"] <= r["arrival_day"]]
    return _fail_list("I2_discharge_after_arrival", "4.2", "discharge_day > arrival_day for every patient",
                      [f"{p}: arrival {a}, discharge {d}" for p, a, d in bad[["patient_id", "arrival_day", "discharge_day"]].itertuples(index=False)])


def check_valid_categories(data) -> CheckResult:
    failures = []
    for table in ("registry", "demand"):
        bad = data[table][~data[table]["department"].isin(DEPARTMENTS)]
        failures += [f"{table} row {i}: department {v!r}" for i, v in bad["department"].items()]
    valid_levels = {str(lv) for lv in LEVELS}
    bad = data["registry"][~data["registry"]["complexity"].astype(str).isin(valid_levels)]
    failures += [f"registry {p}: complexity {c!r}" for p, c in bad[["patient_id", "complexity"]].itertuples(index=False)]
    return _fail_list("I3_valid_categories", "4.2", "All department and complexity values are valid", failures)


def check_resources_days(data) -> CheckResult:
    H = int(data["generation_config"]["horizon_days"])
    days = pd.to_numeric(data["resources"]["day"]).tolist()
    failures = []
    if sorted(days) != list(range(1, H + 1)):
        counts = pd.Series(days).value_counts()
        failures += [f"day {d} appears {counts.get(d, 0)} times" for d in range(1, H + 1) if counts.get(d, 0) != 1]
        failures += [f"unexpected day {d}" for d in sorted(set(days) - set(range(1, H + 1)))]
    return _fail_list("I4_resources_days", "4.2", "Every day 1..H appears exactly once in hospital_resources_daily", failures)


def check_demand_grid(data) -> CheckResult:
    H = int(data["generation_config"]["horizon_days"])
    d = data["demand"].assign(day=pd.to_numeric(data["demand"]["day"]))
    counts = d.groupby(["day", "department"]).size()
    failures = [
        f"(day {day}, {dept}) appears {counts.get((day, dept), 0)} times"
        for day in range(1, H + 1) for dept in DEPARTMENTS
        if counts.get((day, dept), 0) != 1
    ]
    extra = len(d) - H * len(DEPARTMENTS)
    if extra > 0 and not failures:
        failures.append(f"{extra} rows outside the day x department grid")
    return _fail_list("I5_demand_grid", "4.2", "Every day 1..H appears once per department in department_demand_daily", failures)


def check_burn_in(data) -> CheckResult:
    H = int(data["generation_config"]["horizon_days"])
    B = int(data["generation_config"]["burn_in_days"])
    r = _int_frame(data["registry"], ["arrival_day", "discharge_day"])
    failures = [f"{p}: arrival_day {a} outside [{1 - B}, {H}]"
                for p, a in r[["patient_id", "arrival_day"]].itertuples(index=False) if not (1 - B <= a <= H)]
    burn = r[r["arrival_day"] <= 0]
    if burn.empty:
        failures.append("no burn-in patients (arrival_day <= 0)")
    present_day1_burn = burn[burn["discharge_day"] > 1]
    if present_day1_burn.empty:
        failures.append("no burn-in patient is present on day 1: no warm start")
    return _fail_list("I6_burn_in", "4.2",
                      "Burn-in patients have arrival_day <= 0 (within the burn-in window) and some are still present on day 1",
                      failures)


def check_day1_presence(data) -> CheckResult:
    r = _int_frame(data["registry"], ["arrival_day", "discharge_day"])
    d = _int_frame(data["demand"], ["day", *CENSUS_COLS])
    present = r[(r["arrival_day"] <= 1) & (r["discharge_day"] > 1)]
    failures = []
    for dept in DEPARTMENTS:
        row = d[(d["day"] == 1) & (d["department"] == dept)]
        if row.empty:
            failures.append(f"{dept}: no day-1 row")
            continue
        census = int(row[CENSUS_COLS].sum(axis=1).iloc[0])
        n = int((present["department"] == dept).sum())
        if census != n:
            failures.append(f"{dept}: day-1 census {census} != registry patients present on day 1 ({n})")
    return _fail_list("I7_day1_presence", "4.2",
                      "Every patient present on day 1 (including burn-in) is in the registry: day-1 census equals registry presence",
                      failures)


def check_external_event(data) -> CheckResult:
    res = _int_frame(data["resources"], ["day", "total_beds", "total_nurses"]).sort_values("day")
    failures, prev = [], None
    for day, beds, nurses, ev in res[["day", "total_beds", "total_nurses", "external_event"]].itertuples(index=False):
        changed = prev is not None and (beds, nurses) != prev
        has_text = str(ev).strip() != ""
        if changed != has_text:
            failures.append(f"day {day}: pool changed={changed} but external_event={ev!r}")
        prev = (beds, nurses)
    return _fail_list("I9_external_event", "5",
                      "external_event is non-empty exactly on days when a pool changes from the previous day",
                      failures)


# ----------------------------------------------------------------------------- 4.1 reconciliation

def _expected_from_registry(data) -> pd.DataFrame:
    """Independent recomputation of department_demand_daily from patient_registry."""
    H = int(data["generation_config"]["horizon_days"])
    r = _int_frame(data["registry"], ["complexity", "arrival_day", "discharge_day"])
    rows = []
    for day in range(1, H + 1):
        present = r[(r["arrival_day"] <= day) & (r["discharge_day"] > day)]
        census = present.groupby(["department", "complexity"]).size()
        arrivals = r[r["arrival_day"] == day].groupby("department").size()
        discharges = r[r["discharge_day"] == day].groupby("department").size()
        for dept in DEPARTMENTS:
            rows.append({
                "day": day, "department": dept,
                "arrivals": int(arrivals.get(dept, 0)), "discharges": int(discharges.get(dept, 0)),
                **{f"census_L{lv}": int(census.get((dept, lv), 0)) for lv in LEVELS},
            })
    return pd.DataFrame(rows).set_index(["day", "department"])


def _reconcile(data, fields: list[str], check_id: str, description: str) -> CheckResult:
    exp = _expected_from_registry(data)
    act = _int_frame(data["demand"], ["day", "arrivals", "discharges", *CENSUS_COLS]).set_index(["day", "department"])
    failures = []
    for key in exp.index:
        if key not in act.index:
            failures.append(f"day {key[0]} {key[1]}: missing from demand table")
            continue
        for f in fields:
            a, e = int(act.loc[key, f]), int(exp.loc[key, f])
            if a != e:
                failures.append(f"day {key[0]} {key[1]} {f}: demand {a} != registry {e}")
    return _fail_list(check_id, "4.1", description, failures)


def check_reconcile_arrivals(data) -> CheckResult:
    return _reconcile(data, ["arrivals"], "R1_arrivals",
                      "arrivals(d,k) equals registry patients in k with arrival_day = d")


def check_reconcile_discharges(data) -> CheckResult:
    return _reconcile(data, ["discharges"], "R2_discharges",
                      "discharges(d,k) equals registry patients in k with discharge_day = d")


def check_reconcile_census(data) -> CheckResult:
    return _reconcile(data, CENSUS_COLS, "R3_census",
                      "census_Lj(d,k) equals registry level-j patients in k with arrival_day <= d < discharge_day")


def check_census_flow(data) -> CheckResult:
    d = _int_frame(data["demand"], ["day", "arrivals", "discharges", *CENSUS_COLS])
    d["census_total"] = d[CENSUS_COLS].sum(axis=1)
    failures = []
    for dept in DEPARTMENTS:
        s = d[d["department"] == dept].sort_values("day").set_index("day")
        for day in s.index:
            if day - 1 not in s.index:
                continue
            exp = s.loc[day - 1, "census_total"] + s.loc[day, "arrivals"] - s.loc[day, "discharges"]
            if s.loc[day, "census_total"] != exp:
                failures.append(f"day {day} {dept}: census {s.loc[day, 'census_total']} != {exp}")
    return _fail_list("R4_census_flow", "4.1",
                      "census_total(d) = census_total(d-1) + arrivals(d) - discharges(d), for d >= 2", failures)


# ----------------------------------------------------------------------------- 4.3 generation constraints

def check_bed_cap(data) -> CheckResult:
    max_beds = int(data["environment_config"]["max_beds"])
    res = _int_frame(data["resources"], ["day", "total_beds"])
    bad = res[res["total_beds"] > 4 * max_beds]
    return _fail_list("G1_bed_cap_feasibility", "4.3", f"total_beds(t) <= 4 x max_beds (= {4 * max_beds}) for every t",
                      [f"day {d}: total_beds {b}" for d, b in bad[["day", "total_beds"]].itertuples(index=False)])


def check_pools_non_negative(data) -> CheckResult:
    f = _non_negative_int_failures(data["resources"], "resources", ["total_beds", "total_nurses"])
    return _fail_list("G2_pools_non_negative_integers", "4.3", "Pools are non-negative integers on every day", f)


def check_pools_match_schedule(data) -> CheckResult:
    """Independent recomputation of the pools from the base values and the shock schedule."""
    gen = data["generation_config"]
    res = _int_frame(data["resources"], ["day", "total_beds", "total_nurses"])
    failures = []
    for day, beds, nurses in res[["day", "total_beds", "total_nurses"]].itertuples(index=False):
        eb, en = gen["base_pools"]["total_beds"], gen["base_pools"]["total_nurses"]
        for s in gen["shocks"]:
            if s["from_day"] <= day <= s["to_day"]:
                eb += s["delta"] if s["resource"] == "beds" else 0
                en += s["delta"] if s["resource"] == "nurses" else 0
        if (beds, nurses) != (eb, en):
            failures.append(f"day {day}: pools ({beds}, {nurses}) != schedule ({eb}, {en})")
    return _fail_list("G3_pools_match_schedule", "4.3", "Pools equal the base values plus the scheduled shocks", failures)


def check_environment_config(data) -> CheckResult:
    env = data["environment_config"]
    failures = []
    if set(env) != {"max_beds", "w_L1", "w_L2", "w_L3"}:
        failures.append(f"fields {sorted(env)} != ['max_beds', 'w_L1', 'w_L2', 'w_L3']")
    if not (isinstance(env.get("max_beds"), int) and env.get("max_beds", -1) >= 0):
        failures.append(f"max_beds {env.get('max_beds')!r} is not an integer >= 0")
    for w in ("w_L1", "w_L2", "w_L3"):
        if not (isinstance(env.get(w), (int, float)) and env.get(w, -1) >= 0):
            failures.append(f"{w} {env.get(w)!r} is not numeric >= 0")
    return _fail_list("E1_environment_config", "3.4", "environment_config has exactly max_beds and w_L1..w_L3, with valid values", failures)


# ----------------------------------------------------------------------------- runner

CHECKS: list[Callable[[dict], CheckResult]] = [
    check_schema,
    check_integer_fields,
    check_environment_config,
    check_unique_ids,
    check_id_format_and_order,
    check_discharge_after_arrival,
    check_valid_categories,
    check_resources_days,
    check_demand_grid,
    check_burn_in,
    check_day1_presence,
    check_external_event,
    check_reconcile_arrivals,
    check_reconcile_discharges,
    check_reconcile_census,
    check_census_flow,
    check_bed_cap,
    check_pools_non_negative,
    check_pools_match_schedule,
]


def run_checks(data: dict) -> list[CheckResult]:
    results = []
    schema = check_schema(data)
    for check in CHECKS:
        name = check.__name__
        if check is check_schema:
            results.append(schema)
            continue
        if not schema.passed and check is not check_environment_config:
            results.append(CheckResult(name, "-", f"{name} not run: schema check failed", False, 1, ["skipped"]))
            continue
        try:
            results.append(check(data))
        except Exception as exc:  # malformed data must fail the check, never crash validation
            results.append(CheckResult(name, "-", f"{name} raised an error", False, 1, [f"{type(exc).__name__}: {exc}"]))
    return results


def validate_dataset(root: str | Path, dataset_id: str, write_report: bool = True) -> dict:
    data = load_dataset(root, dataset_id)
    results = run_checks(data)
    report = {
        "dataset_id": dataset_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "writer": "src.data_generation.validation",
        "accepted": all(r.passed for r in results),
        "n_checks": len(results),
        "n_passed": sum(r.passed for r in results),
        "checks": [asdict(r) for r in results],
    }
    if write_report:
        out = Path(root) / "data" / "processed" / dataset_id
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "validation_report.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
    return report
