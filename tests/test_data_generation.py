"""Tests for the generator and for every check in DATA_DICTIONARY.md §4.

Each check is shown to pass on a generated dataset and to fail on a deliberately corrupted copy.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data_generation.generator import (
    external_event, generate, load_json, pools_for_day, write_dataset,
)
from src.data_generation.los import calibrate, ceil_moments
from src.data_generation.stats import n1_requirement
from src.data_generation.validation import load_dataset, run_checks, validate_dataset

CONFIG_DIR = Path(__file__).resolve().parents[1] / "src" / "data_generation" / "configs"
GEN = load_json(CONFIG_DIR / "generation_config.json")
ENV = load_json(CONFIG_DIR / "environment_config.json")
SEED = 20261107


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    root = tmp_path_factory.mktemp("data_root")
    ds = generate(GEN, ENV, SEED)
    write_dataset(ds, root)
    return root, ds


@pytest.fixture
def data(written):
    root, ds = written
    return load_dataset(root, ds.dataset_id)


def results_by_id(data):
    return {r.check_id: r for r in run_checks(data)}


# ----------------------------------------------------------------------------- LOS calibration

@pytest.mark.parametrize("level,target", [(1, 3), (2, 5), (3, 8)])
def test_los_calibration_hits_discrete_mean(level, target):
    cal = calibrate(0.6, {1: 3, 2: 5, 3: 8})
    mean, _ = ceil_moments(cal["mu"][level], cal["sigma"])
    assert mean == pytest.approx(target, abs=1e-9)
    assert cal["sigma"] == pytest.approx(np.sqrt(np.log(1.36)))


# ----------------------------------------------------------------------------- generator properties

def test_generator_is_deterministic():
    a, b = generate(GEN, ENV, SEED), generate(GEN, ENV, SEED)
    pd.testing.assert_frame_equal(a.registry, b.registry)
    pd.testing.assert_frame_equal(a.demand, b.demand)


def test_different_seeds_differ():
    assert not generate(GEN, ENV, 1).registry.equals(generate(GEN, ENV, 2).registry)


def test_pool_schedule():
    assert pools_for_day(GEN, 1) == (96, 37)
    assert pools_for_day(GEN, 8) == (96, 33) and pools_for_day(GEN, 11) == (96, 37)
    assert pools_for_day(GEN, 16) == (100, 37) and pools_for_day(GEN, 21) == (96, 37)
    assert pools_for_day(GEN, 23) == (86, 37) and pools_for_day(GEN, 26) == (96, 37)


def _change_days(cfg):
    H = int(cfg["horizon_days"])
    pools = [pools_for_day(cfg, t) for t in range(1, H + 1)]
    return [t for t in range(2, H + 1) if pools[t - 1] != pools[t - 2]]


def test_external_event_only_on_change_days(written):
    _, ds = written
    with_text = ds.resources.loc[ds.resources["external_event"] != "", "day"].tolist()
    assert with_text == _change_days(GEN) == [8, 11, 16, 21, 23, 26]   # approved schedule
    assert external_event((96, 37), (86, 37)) == "bed pool reduced by 10"
    assert external_event((100, 37), (78, 37)) == "bed pool reduced by 22"
    assert external_event((96, 33), (100, 37)) == "bed pool increased by 4; nurse pool increased by 4"
    assert external_event(None, (96, 37)) == ""


def _candidate(shock2, shock3):
    cfg = copy.deepcopy(GEN)
    cfg["shocks"] = [s for s in cfg["shocks"] if s["resource"] == "nurses"] + [shock2, shock3]
    return cfg


CANDIDATES = {
    "A26": _candidate({"resource": "beds", "delta": 4, "from_day": 16, "to_day": 20},
                      {"resource": "beds", "delta": -26, "from_day": 23, "to_day": 25}),
    "B18": _candidate({"resource": "beds", "delta": 4, "from_day": 16, "to_day": 18},
                      {"resource": "beds", "delta": -18, "from_day": 19, "to_day": 21}),
    "C18": _candidate({"resource": "beds", "delta": 4, "from_day": 16, "to_day": 20},
                      {"resource": "beds", "delta": -18, "from_day": 21, "to_day": 23}),
}


@pytest.mark.parametrize("name", sorted(CANDIDATES))
def test_candidate_schedules_validate_and_mark_only_change_days(tmp_path, name):
    """Any Shock 3 candidate passes every check; adjacent shocks yield a single change event."""
    cfg = CANDIDATES[name]
    ds = generate(cfg, ENV, SEED)
    write_dataset(ds, tmp_path)
    report = validate_dataset(tmp_path, ds.dataset_id, write_report=False)
    assert report["accepted"], [c for c in report["checks"] if not c["passed"]]
    with_text = ds.resources.loc[ds.resources["external_event"] != "", "day"].tolist()
    assert with_text == _change_days(cfg)
    if name == "B18":   # +4 ends on day 18 and the cut starts on day 19: one event, 100 -> 78
        assert ds.resources.set_index("day").loc[19, "external_event"] == "bed pool reduced by 22"


def test_demand_is_written_from_counters_not_registry():
    """The generator module must not derive the demand table from the registry."""
    src = (Path(__file__).resolve().parents[1] / "src" / "data_generation" / "generator.py").read_text(encoding="utf-8")
    assert "groupby" not in src and "registry[" not in src


def test_existing_raw_data_is_not_overwritten(written):
    root, ds = written
    with pytest.raises(FileExistsError):
        write_dataset(ds, root)


def test_n1_requirement_is_exact():
    # 0.2*12 + 0.6*1 = 3.0000000000000004 in floating point; the exact requirement is 3
    env = {"w_L1": 0.20, "w_L2": 0.35, "w_L3": 0.60}
    assert int(n1_requirement(12, 0, 1, env)) == 3
    assert int(n1_requirement(0, 20, 0, env)) == 7
    assert int(n1_requirement(5, 0, 0, env)) == 1
    assert int(n1_requirement(1, 1, 1, env)) == 2


# ----------------------------------------------------------------------------- all checks pass

def test_generated_dataset_passes_every_check(written):
    root, ds = written
    report = validate_dataset(root, ds.dataset_id, write_report=False)
    failed = [c for c in report["checks"] if not c["passed"]]
    assert report["accepted"], failed
    assert report["n_checks"] == 19


# ----------------------------------------------------------------------------- each check detects corruption

def _set(df: pd.DataFrame, idx, col, value) -> pd.DataFrame:
    df = df.copy()
    df.loc[idx, col] = str(value)
    return df


def corrupt_arrivals(d):
    i = d["demand"].index[(d["demand"]["day"] == "5")][0]
    d["demand"] = _set(d["demand"], i, "arrivals", int(d["demand"].loc[i, "arrivals"]) + 1)


def corrupt_discharges(d):
    i = d["demand"].index[(d["demand"]["day"] == "7")][1]
    d["demand"] = _set(d["demand"], i, "discharges", int(d["demand"].loc[i, "discharges"]) + 1)


def corrupt_census(d):
    i = d["demand"].index[(d["demand"]["day"] == "12")][2]
    d["demand"] = _set(d["demand"], i, "census_L3", int(d["demand"].loc[i, "census_L3"]) + 1)


def corrupt_census_flow(d):
    # move one patient between levels on one day: census totals, arrivals and discharges stay
    # consistent with the registry for R1/R2, but R3 and R4 must catch the change in total
    i = d["demand"].index[(d["demand"]["day"] == "20")][0]
    d["demand"] = _set(d["demand"], i, "census_L1", int(d["demand"].loc[i, "census_L1"]) + 2)


def corrupt_duplicate_id(d):
    d["registry"] = _set(d["registry"], 1, "patient_id", d["registry"].loc[0, "patient_id"])


def corrupt_id_format(d):
    d["registry"] = _set(d["registry"], 3, "patient_id", "X1")


def corrupt_id_order(d):
    reg = d["registry"].copy()
    last = len(reg) - 1
    reg.loc[0, "patient_id"], reg.loc[last, "patient_id"] = reg.loc[last, "patient_id"], reg.loc[0, "patient_id"]
    d["registry"] = reg


def corrupt_discharge_before_arrival(d):
    d["registry"] = _set(d["registry"], 10, "discharge_day", d["registry"].loc[10, "arrival_day"])


def corrupt_department(d):
    d["registry"] = _set(d["registry"], 5, "department", "pediatrics")


def corrupt_complexity(d):
    d["registry"] = _set(d["registry"], 5, "complexity", 4)


def corrupt_resources_day(d):
    d["resources"] = _set(d["resources"], 4, "day", 4)  # day 5 replaced by a duplicate day 4


def corrupt_demand_grid(d):
    d["demand"] = d["demand"].drop(index=d["demand"].index[7])


def corrupt_burn_in(d):
    reg = d["registry"].copy()
    reg["arrival_day"] = reg["arrival_day"].astype(int)
    reg.loc[reg["arrival_day"] <= 0, "arrival_day"] = -100
    reg["arrival_day"] = reg["arrival_day"].astype(str)
    d["registry"] = reg


def corrupt_day1(d):
    i = d["demand"].index[(d["demand"]["day"] == "1")][0]
    d["demand"] = _set(d["demand"], i, "census_L2", int(d["demand"].loc[i, "census_L2"]) - 1)


def corrupt_external_event_missing(d):
    d["resources"] = _set(d["resources"], 7, "external_event", "")


def corrupt_external_event_spurious(d):
    d["resources"] = _set(d["resources"], 2, "external_event", "bed pool reduced by 10 for 3 days")


def corrupt_bed_cap(d):
    d["resources"] = _set(d["resources"], 0, "total_beds", 161)


def corrupt_negative_pool(d):
    d["resources"] = _set(d["resources"], 0, "total_nurses", -1)


def corrupt_pool_schedule(d):
    d["resources"] = _set(d["resources"], 24, "total_beds", 90)  # day 25 should be 86


def corrupt_non_integer(d):
    d["demand"] = _set(d["demand"], 0, "arrivals", "2.5")


def corrupt_env(d):
    d["environment_config"] = {**d["environment_config"], "max_beds": -1}


def corrupt_schema(d):
    d["registry"] = d["registry"].rename(columns={"discharge_day": "discharge"})


CASES = [
    (corrupt_arrivals, "R1_arrivals"),
    (corrupt_discharges, "R2_discharges"),
    (corrupt_census, "R3_census"),
    (corrupt_census, "R4_census_flow"),
    (corrupt_census_flow, "R4_census_flow"),
    (corrupt_duplicate_id, "I1_unique_patient_id"),
    (corrupt_id_format, "I1b_patient_id_format_order"),
    (corrupt_id_order, "I1b_patient_id_format_order"),
    (corrupt_discharge_before_arrival, "I2_discharge_after_arrival"),
    (corrupt_department, "I3_valid_categories"),
    (corrupt_complexity, "I3_valid_categories"),
    (corrupt_resources_day, "I4_resources_days"),
    (corrupt_demand_grid, "I5_demand_grid"),
    (corrupt_burn_in, "I6_burn_in"),
    (corrupt_day1, "I7_day1_presence"),
    (corrupt_external_event_missing, "I9_external_event"),
    (corrupt_external_event_spurious, "I9_external_event"),
    (corrupt_bed_cap, "G1_bed_cap_feasibility"),
    (corrupt_negative_pool, "G2_pools_non_negative_integers"),
    (corrupt_pool_schedule, "G3_pools_match_schedule"),
    (corrupt_non_integer, "I8_integer_fields"),
    (corrupt_env, "E1_environment_config"),
    (corrupt_schema, "I0_schema"),
]


@pytest.mark.parametrize("corrupt,check_id", CASES, ids=[f"{c.__name__}->{k}" for c, k in CASES])
def test_check_detects_corruption(data, corrupt, check_id):
    d = copy.deepcopy(data)
    corrupt(d)
    results = results_by_id(d)
    assert check_id in results, sorted(results)
    assert not results[check_id].passed


def test_every_check_has_a_corruption_test():
    from src.data_generation.validation import CHECKS
    tested = {k for _, k in CASES}
    ids = {r.check_id for r in run_checks(load_dataset_like_generated())}
    assert ids <= tested, ids - tested
    assert len(CHECKS) == len(ids)


def load_dataset_like_generated():
    ds = generate(GEN, ENV, 1)
    as_str = lambda df: df.astype(str)  # noqa: E731
    return {
        "resources": as_str(ds.resources), "demand": as_str(ds.demand), "registry": as_str(ds.registry),
        "environment_config": ds.environment_config, "generation_config": ds.generation_config,
    }


def test_malformed_data_fails_without_crashing(data):
    d = copy.deepcopy(data)
    d["registry"] = _set(d["registry"], 0, "arrival_day", "abc")
    results = run_checks(d)
    assert any(not r.passed for r in results)
