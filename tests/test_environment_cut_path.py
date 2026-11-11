"""Unit and property tests for the shock-cut path (CLAUDE.md §10.E.3–4, §10.F.3, §10.G;
PROJECT_SPEC.md §5.1, §5.3, §5.5, §5.7).

Covers: largest remainder, the repair rule's cut step, the intra-department shock cut, the
validator's EVICTION / SHOCK_OVERCUT codes, and an end-to-end replay on generated data with a
shock large enough to force cuts.
"""

from __future__ import annotations

import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.data_generation.generator import generate, load_json, pools_for_day
from src.data_generation.stats import n1_requirement as stats_n1
from src.environment.allocation import InfeasibleError, largest_remainder
from src.environment.bed_assignment import assign_beds
from src.environment.nurses import requirement as env_n1
from src.environment.repair import repair_beds, repair_nurses
from src.environment.types import Patient, cut_order_key, occupied_by_department
from src.environment.validator import validate
from src.utils.constants import DEPARTMENTS

MAX_BEDS = 40
IM, CA, NE, OR = DEPARTMENTS
CONFIG_DIR = Path(__file__).resolve().parents[1] / "src" / "data_generation" / "configs"
ENV = load_json(CONFIG_DIR / "environment_config.json")


def P(num, dept, level, arrival):
    return Patient(f"P{num:06d}", dept, level, arrival)


def codes(violations):
    return {v.code for v in violations}


def nurses_ok(total=37):
    return dict(zip(DEPARTMENTS, largest_remainder(total, [1, 1, 1, 1])))


# ============================================================================ largest remainder

def test_lr_department_order_breaks_ties():
    assert largest_remainder(10, [1, 1, 1]) == [4, 3, 3]


def test_lr_redistributes_capped_units():
    # quotas 8, 1, 1; the first is capped at 5; 3 units go over the others (1.5, 1.5), tie to order
    assert largest_remainder(10, [8, 1, 1], caps=[5, 10, 10]) == [5, 3, 2]


def test_lr_zero_weights_split_equally():
    assert largest_remainder(6, [0, 0, 0]) == [2, 2, 2]


def test_lr_infeasible_caps():
    with pytest.raises(InfeasibleError):
        largest_remainder(10, [1, 1], caps=[4, 5])


@given(total=st.integers(0, 200),
       weights=st.lists(st.integers(0, 50), min_size=4, max_size=4),
       caps=st.lists(st.integers(0, 60), min_size=4, max_size=4))
def test_lr_properties(total, weights, caps):
    if sum(caps) < total:
        with pytest.raises(InfeasibleError):
            largest_remainder(total, weights, caps)
        return
    a = largest_remainder(total, weights, caps)
    assert sum(a) == total
    assert all(0 <= x <= c for x, c in zip(a, caps))
    uncapped = largest_remainder(total, weights)
    W = sum(weights) or len(weights)
    w = weights if sum(weights) else [1] * len(weights)
    assert all(abs(x - Fraction(total * wi, W)) < 1 for x, wi in zip(uncapped, w))


# ============================================================================ unit: repair cut step

def _scenario_no_free_beds():
    holders = [
        P(1, IM, 3, -2), P(10, IM, 1, 5),      # IM: L3 and a recent L1
        P(5, CA, 1, 3), P(6, CA, 2, 3),        # Cardiology: an older L1 and an L2
        P(7, NE, 2, 1),
        P(8, OR, 3, 0),
    ]
    prev = {IM: 2, CA: 2, NE: 1, OR: 1}        # every bed occupied
    return holders, prev


def test_repair_cuts_lowest_level_most_recent_first():
    holders, prev = _scenario_no_free_beds()
    beds, cut = repair_beds(prev, 5, MAX_BEDS, holders)
    assert cut == ("P000010",)                 # L1, arrival 5 beats L1 arrival 3
    assert beds == {IM: 1, CA: 2, NE: 1, OR: 1}


def test_repair_cut_ties_on_arrival_go_to_higher_patient_id():
    holders = [P(3, IM, 1, 4), P(9, CA, 1, 4)]
    beds, cut = repair_beds({IM: 1, CA: 1, NE: 0, OR: 0}, 1, MAX_BEDS, holders)
    assert cut == ("P000009",) and beds == {IM: 1, CA: 0, NE: 0, OR: 0}


def test_repair_removes_free_beds_before_occupied_ones():
    holders, prev = _scenario_no_free_beds()
    prev = {**prev, NE: 4}                     # NE now has 3 free beds; pool drops by 3
    beds, cut = repair_beds(prev, 6, MAX_BEDS, holders)
    assert cut == () and beds == {IM: 2, CA: 2, NE: 1, OR: 1}
    beds, cut = repair_beds(prev, 5, MAX_BEDS, holders)   # 4 beds lost: 3 free, then 1 occupied
    assert cut == ("P000010",) and beds == {IM: 1, CA: 2, NE: 1, OR: 1}


def test_repair_increase_respects_cap():
    beds, cut = repair_beds({IM: 40, CA: 20, NE: 20, OR: 16}, 100, MAX_BEDS, [])
    assert cut == () and beds[IM] == 40 and sum(beds.values()) == 100


def test_repair_nurses_shock_and_restore():
    prev = {IM: 12, CA: 10, NE: 8, OR: 7}
    down = repair_nurses(prev, 33, {d: 0 for d in DEPARTMENTS})
    assert sum(down.values()) == 33 and all(down[d] <= prev[d] for d in DEPARTMENTS)
    up = repair_nurses(down, 37, {d: 0 for d in DEPARTMENTS})
    assert sum(up.values()) == 37


# ============================================================================ unit: validator on the cut path

def test_validator_accepts_exact_cut_in_any_department():
    occ = {IM: 2, CA: 2, NE: 1, OR: 1}       # sum of occupied = 6 > pool 5: shortfall 1
    for absorbing in DEPARTMENTS:            # the ALLOCATOR chooses which department absorbs the cut
        beds = {**occ, absorbing: occ[absorbing] - 1}
        assert validate(beds, nurses_ok(), 5, 37, MAX_BEDS, occ) == []


def test_validator_rejects_overcut():
    occ = {IM: 2, CA: 2, NE: 1, OR: 1}
    beds = {IM: 0, CA: 2, NE: 1, OR: 2}      # 2 cut in IM, 1 bed left free in OR; shortfall is 1
    assert codes(validate(beds, nurses_ok(), 5, 37, MAX_BEDS, occ)) == {"SHOCK_OVERCUT"}


def test_validator_rejects_eviction_without_shock():
    occ = {IM: 20, CA: 20, NE: 20, OR: 20}
    beds = {IM: 19, CA: 21, NE: 28, OR: 28}  # pool 96 covers all 80 occupied beds
    assert codes(validate(beds, nurses_ok(), 96, 37, MAX_BEDS, occ)) == {"EVICTION"}


def test_validator_other_codes():
    occ = {d: 0 for d in DEPARTMENTS}
    assert codes(validate({IM: 41, CA: 20, NE: 20, OR: 15}, nurses_ok(), 96, 37, MAX_BEDS, occ)) == {"BOUNDS"}
    assert codes(validate({IM: 40, CA: 20, NE: 20, OR: 15}, nurses_ok(), 96, 37, MAX_BEDS, occ)) == {"CONSERVATION_BEDS"}
    assert codes(validate({IM: 40, CA: 20, NE: 20, OR: 16}, nurses_ok(36), 96, 37, MAX_BEDS, occ)) == {"CONSERVATION_NURSES"}
    assert codes(validate({IM: 40.0, CA: 20, NE: 20, OR: 16}, nurses_ok(), 96, 37, MAX_BEDS, occ)) == {"INTEGRALITY"}
    assert codes(validate({IM: True, CA: 20, NE: 20, OR: 55}, nurses_ok(), 96, 37, MAX_BEDS, occ)) == {"INTEGRALITY"}


# ============================================================================ unit: intra-department cut

def test_bed_assignment_cuts_lowest_level_in_department():
    present = [P(1, IM, 3, -2), P(2, IM, 1, 0), P(3, IM, 1, 2), P(4, IM, 2, 3), P(11, IM, 3, 6)]
    holders = {"P000001", "P000002", "P000003", "P000004"}
    a = assign_beds({IM: 2, CA: 0, NE: 0, OR: 0}, present, holders)
    assert a.evicted == {"P000003", "P000002"}           # both L1, most recent first
    assert a.in_bed == {"P000001", "P000004"}
    assert a.admitted == frozenset()                     # no free bed for the new L3 patient
    assert a.overflow == {"P000002", "P000003", "P000011"}


# ============================================================================ property tests

@st.composite
def cut_scenarios(draw, pool_mode: str = "any"):
    """Random hospital state at the start of day t: holders (O_d), overflow, previous allocation, new pool."""
    raw = []
    prev = {}
    for dept in DEPARTMENTS:
        n_hold = draw(st.integers(0, MAX_BEDS))
        n_over = draw(st.integers(0, 6))
        extra = draw(st.integers(0, MAX_BEDS - n_hold))
        prev[dept] = n_hold + extra
        for k in range(n_hold + n_over):
            raw.append((draw(st.integers(-29, 30)), dept, draw(st.integers(1, 3)), k < n_hold))
    raw.sort(key=lambda r: r[0])                         # IDs follow arrival order
    patients = [Patient(f"P{i + 1:06d}", d, lv, arr) for i, (arr, d, lv, _) in enumerate(raw)]
    holders = [p for p, r in zip(patients, raw) if r[3]]
    n_occ = len(holders)
    if pool_mode == "shortfall":           # the pool falls below the occupied beds: a cut is forced
        assume(n_occ > 0)
        pool = draw(st.integers(0, n_occ - 1))
    elif pool_mode == "no_shortfall":
        pool = draw(st.integers(n_occ, 4 * MAX_BEDS))
    else:
        pool = draw(st.integers(0, 4 * MAX_BEDS))
    return patients, holders, prev, pool


PROPS = settings(max_examples=300, deadline=None,
                 suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])


@PROPS
@given(st.one_of(cut_scenarios(), cut_scenarios("shortfall")))
def test_repair_always_valid_and_cuts_exactly_the_shortfall(s):
    patients, holders, prev, pool = s
    occ = occupied_by_department(holders)
    beds, cut = repair_beds(prev, pool, MAX_BEDS, holders)
    assert validate(beds, nurses_ok(), pool, 37, MAX_BEDS, occ) == []
    shortfall = max(0, sum(occ.values()) - pool)
    assert len(cut) == shortfall
    assert sum(max(0, occ[d] - beds[d]) for d in DEPARTMENTS) == shortfall
    if shortfall:
        assert all(beds[d] <= occ[d] for d in DEPARTMENTS)       # no free bed survives a forced cut
    else:
        assert all(beds[d] >= occ[d] for d in DEPARTMENTS)       # no-eviction


@PROPS
@given(st.one_of(cut_scenarios(), cut_scenarios("shortfall")))
def test_repair_cut_has_no_clinical_shock_violation(s):
    """§10.G: never cut a level-k bed while a lower-level bed elsewhere could have been cut."""
    _, holders, prev, pool = s
    _, cut = repair_beds(prev, pool, MAX_BEDS, holders)
    cut_set = set(cut)
    kept = [p for p in holders if p.patient_id not in cut_set]
    ordered = sorted(holders, key=cut_order_key)
    assert list(cut) == [p.patient_id for p in ordered[:len(cut)]]
    if cut and kept:
        assert max(p.complexity for p in holders if p.patient_id in cut_set) <= min(p.complexity for p in kept)


@PROPS
@given(st.one_of(cut_scenarios(), cut_scenarios("shortfall")))
def test_bed_assignment_evicts_exactly_the_repair_cut(s):
    """The hospital-wide repair cut and the per-department assignment cut pick the same patients."""
    patients, holders, prev, pool = s
    beds, cut = repair_beds(prev, pool, MAX_BEDS, holders)
    a = assign_beds(beds, patients, {p.patient_id for p in holders})
    assert a.evicted == set(cut)
    assert a.in_bed | a.overflow == {p.patient_id for p in patients}
    assert not (a.in_bed & a.overflow)
    for d in DEPARTMENTS:
        present_d = [p for p in patients if p.department == d]
        assert len([p for p in present_d if p.patient_id in a.in_bed]) == min(beds[d], len(present_d))


@PROPS
@given(cut_scenarios("shortfall"), st.data())
def test_validator_accepts_every_exact_cut_and_rejects_one_more(s, data):
    _, holders, _, pool = s
    occ = occupied_by_department(holders)
    shortfall = sum(occ.values()) - pool
    assume(shortfall > 0)
    # any split of the shortfall across departments (the ALLOCATOR's choice) is valid
    beds = dict(occ)
    for _ in range(shortfall):
        d = data.draw(st.sampled_from([d for d in DEPARTMENTS if beds[d] > 0]))
        beds[d] -= 1
    assert validate(beds, nurses_ok(), pool, 37, MAX_BEDS, occ) == []
    # cutting one more bed and leaving it free elsewhere keeps conservation but over-cuts
    donors = [d for d in DEPARTMENTS if beds[d] > 0]
    # the receiver must not itself be cut, so that the moved bed becomes a free bed
    receivers = [d for d in DEPARTMENTS if beds[d] >= occ[d] and beds[d] < MAX_BEDS]
    assume(donors and receivers)
    src = data.draw(st.sampled_from(donors))
    assume([d for d in receivers if d != src])
    dst = data.draw(st.sampled_from([d for d in receivers if d != src]))
    over = {**beds, src: beds[src] - 1, dst: beds[dst] + 1}
    assert "SHOCK_OVERCUT" in codes(validate(over, nurses_ok(), pool, 37, MAX_BEDS, occ))


@PROPS
@given(cut_scenarios("no_shortfall"), st.data())
def test_validator_rejects_any_eviction_without_shortfall(s, data):
    _, holders, _, pool = s
    occ = occupied_by_department(holders)
    assume(sum(occ.values()) <= pool)
    beds, _ = repair_beds(dict(occ), pool, MAX_BEDS, holders)   # a valid allocation: B_d >= O_d
    victims = [d for d in DEPARTMENTS if occ[d] > 0]
    assume(victims)
    v = data.draw(st.sampled_from(victims))
    receivers = [d for d in DEPARTMENTS if d != v and beds[d] < MAX_BEDS]
    assume(receivers)
    r = data.draw(st.sampled_from(receivers))
    shift = beds[v] - occ[v] + 1                         # take v one bed below its occupied count
    assume(beds[r] + shift <= MAX_BEDS)
    bad = {**beds, v: beds[v] - shift, r: beds[r] + shift}
    assert "EVICTION" in codes(validate(bad, nurses_ok(), pool, 37, MAX_BEDS, occ))


@given(prev=st.lists(st.integers(0, 20), min_size=4, max_size=4), pool=st.integers(0, 80))
def test_repair_nurses_conserves(prev, pool):
    out = repair_nurses(dict(zip(DEPARTMENTS, prev)), pool, dict(zip(DEPARTMENTS, [3, 2, 1, 1])))
    assert sum(out.values()) == pool and all(x >= 0 for x in out.values())


# ============================================================================ N1: two independent implementations agree

def test_n1_environment_matches_stats_implementation():
    grid = np.array([(a, b, c) for a in range(0, 41) for b in range(0, 41) for c in range(0, 41, 3)])
    s = stats_n1(grid[:, 0], grid[:, 1], grid[:, 2], ENV)
    e = [env_n1(int(a), int(b), int(c), ENV) for a, b, c in grid]
    assert list(s) == e


# ============================================================================ end to end on generated data

def _replay_with_repair(gen_cfg, seed):
    """B0-style replay: initial allocation, then the repair rule and bed assignment every day."""
    ds = generate(gen_cfg, ENV, seed)
    reg = [Patient(r.patient_id, r.department, int(r.complexity), int(r.arrival_day)) for r in ds.registry.itertuples()]
    dis = dict(zip(ds.registry.patient_id, ds.registry.discharge_day.astype(int)))
    H = int(gen_cfg["horizon_days"])
    in_bed: set[str] = set()
    beds = None
    log = []
    for t in range(1, H + 1):
        present = [p for p in reg if p.arrival_day <= t < dis[p.patient_id]]
        pid_present = {p.patient_id for p in present}
        holders = [p for p in present if p.patient_id in in_bed]
        pool_b, _ = pools_for_day(gen_cfg, t)
        if t == 1:
            census = [sum(p.department == d for p in present) for d in DEPARTMENTS]
            beds = dict(zip(DEPARTMENTS, largest_remainder(pool_b, census, caps=[MAX_BEDS] * 4)))
            cut = ()
        else:
            beds, cut = repair_beds(beds, pool_b, MAX_BEDS, holders)
        occ = occupied_by_department(holders)
        v = validate(beds, nurses_ok(), pool_b, 37, MAX_BEDS, occ)
        a = assign_beds(beds, present, {p.patient_id for p in holders})
        log.append((t, sum(occ.values()), pool_b, len(cut), v, a.evicted == set(cut)))
        in_bed = set(a.in_bed) & pid_present
    return log


def test_end_to_end_replay_exercises_cut_path():
    gen = load_json(CONFIG_DIR / "generation_config.json")
    strong = copy.deepcopy(gen)
    strong["shocks"] = [s for s in strong["shocks"] if not (s["resource"] == "beds" and s["delta"] < 0)]
    strong["shocks"].append({"resource": "beds", "delta": -40, "from_day": 23, "to_day": 25})
    log = _replay_with_repair(strong, 20261107)
    assert all(v == [] and same for _, _, _, _, v, same in log)
    t23 = next(row for row in log if row[0] == 23)
    assert t23[3] == t23[1] - t23[2] > 0            # cut exactly the shortfall, and a cut happened
