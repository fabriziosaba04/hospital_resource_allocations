"""Tests for the rest of the environment: initial allocation, coverage C1, nurse tier maxima, the bed
pairing detector and the what-if (PROJECT_SPEC.md §5.2, §5.4, §5.6; EVALUATION_PLAN.md §3.1–§3.2).

Cross-checks the environment against the audit's independent implementations:
  - nurse closed form (Fraction, three cases) vs enumeration of every integer allocation;
  - bed pairing (environment) vs closed form Max_j (audit), on normal and on shock days.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import product

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.environment.bed_assignment import assign_beds
from src.environment.clinical import bed_pairs
from src.environment.initial import initial_allocation
from src.environment.nurses import coverage, max_tier_coverage, need_by_level, tier_gaps
from src.environment.types import Patient, cut_order_key
from src.environment.whatif import DayContext, simulate
from src.evaluation.audit import bed_tier_max, compositions
from src.evaluation.baselines import b1
from src.utils.constants import DEPARTMENTS, LEVELS

IM, CA, NE, OR = DEPARTMENTS
F = Fraction
ENV = {"max_beds": 40, "w_L1": 0.2, "w_L2": 0.35, "w_L3": 0.6}
PROPS = settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])


# ============================================================================ initial allocation

def test_initial_allocation_proportional_and_capped():
    beds, nurses = initial_allocation(96, 37, {IM: 30, CA: 20, NE: 10, OR: 36},
                                      {IM: 12, CA: 10, NE: 6, OR: 8}, max_beds=40)
    assert sum(beds.values()) == 96 and sum(nurses.values()) == 37
    assert beds == {IM: 30, CA: 20, NE: 10, OR: 36}           # exact quotas (census sums to 96)
    assert nurses == {IM: 13, CA: 10, NE: 6, OR: 8}           # quotas 12.33, 10.28, 6.17, 8.22: the spare unit goes to IM (.33)


def test_initial_allocation_respects_cap():
    beds, _ = initial_allocation(100, 10, {IM: 80, CA: 10, NE: 5, OR: 5}, {IM: 1, CA: 1, NE: 1, OR: 1}, max_beds=40)
    assert beds[IM] == 40 and sum(beds.values()) == 100 and max(beds.values()) <= 40


# ============================================================================ coverage C1

def test_coverage_covers_highest_level_first():
    need = need_by_level({1: 5, 2: 2, 3: 1}, ENV)            # 1.0, 0.7, 0.6
    covered, shortage = coverage(2, need)
    assert covered == {3: F(3, 5), 2: F(7, 10), 1: F(7, 10)}
    assert shortage == {3: 0, 2: 0, 1: F(3, 10)}


def test_coverage_zero_nurses():
    covered, shortage = coverage(0, need_by_level({1: 1, 2: 1, 3: 1}, ENV))
    assert all(v == 0 for v in covered.values()) and shortage[3] == F(3, 5)


# ============================================================================ nurse tier maxima (Log #46)

def brute_max(pool, a):
    return max(sum(min(F(n), x) for n, x in zip(N, a)) for N in product(range(pool + 1), repeat=len(a))
               if sum(N) == pool)


def test_max_tier_coverage_three_cases_by_hand():
    a = [F(12, 5), F(18, 5), F(6, 5), F(0)]                  # 2.4, 3.6, 1.2, 0: floors 6, ceilings 9, total 7.2
    assert max_tier_coverage(4, a) == 4                     # P_N < sum floor: every nurse covers a full unit
    assert max_tier_coverage(6, a) == 6                     # P_N = sum floor
    assert max_tier_coverage(7, a) == F(33, 5)              # 6 + 0.6 (largest fractional part)
    assert max_tier_coverage(8, a) == 7                     # 6 + 0.6 + 0.4
    assert max_tier_coverage(9, a) == F(36, 5)              # everything covered
    # the two-case form of the proposal (REFLECTION_LOG R17) would give 6 for P_N = 4
    for p in range(0, 11):
        assert max_tier_coverage(p, a) == brute_max(p, a)


@pytest.mark.slow
@PROPS
@given(st.integers(0, 14), st.lists(st.integers(0, 60), min_size=4, max_size=4))
def test_max_tier_coverage_matches_enumeration(pool, a20):
    a = [F(x, 20) for x in a20]                             # multiples of 0.05, as with the N1 weights
    assert max_tier_coverage(pool, a) == brute_max(pool, a)


@pytest.mark.slow
@PROPS
@given(st.integers(0, 40), st.lists(st.tuples(st.integers(0, 15), st.integers(0, 15), st.integers(0, 10)),
                                    min_size=4, max_size=4))
def test_tier_gaps_closed_form_vs_audit_enumeration(pool, counts):
    needs = {d: need_by_level({1: c[0], 2: c[1], 3: c[2]}, ENV) for d, c in zip(DEPARTMENTS, counts)}
    comp = compositions(pool)
    for j in LEVELS:
        a = [sum((needs[d][k] for k in LEVELS if k >= j), F(0)) for d in DEPARTMENTS]
        best = max(sum(min(F(int(n)), x) for n, x in zip(row, a)) for row in comp)
        assert max_tier_coverage(pool, a) == best
    nurses = dict(zip(DEPARTMENTS, comp[len(comp) // 2].tolist()))
    assert all(g >= 0 for g in tier_gaps(nurses, needs, pool).values())


# ============================================================================ bed pairing vs closed form

def _day(draw_levels, holders_per_dept, waiting_per_dept):
    """Build present patients: holders and non-holders per department, with ids in arrival order."""
    present, holder_ids, num = [], set(), 0
    for d, hs, ws in zip(DEPARTMENTS, holders_per_dept, waiting_per_dept):
        for lvl in hs:
            num += 1
            p = Patient(f"P{num:06d}", d, lvl, -num)
            present.append(p)
            holder_ids.add(p.patient_id)
        for lvl in ws:
            num += 1
            present.append(Patient(f"P{num:06d}", d, lvl, num % 7 - 3))
    return present, holder_ids


levels = st.integers(1, 3)
dept_lists = st.lists(st.lists(levels, max_size=6), min_size=4, max_size=4)


@pytest.mark.slow
@PROPS
@given(dept_lists, dept_lists, st.integers(3, 8), st.data())
def test_pairing_equals_closed_form_normal_day(hold, wait, cap, data):
    hold = [h[:cap] for h in hold]
    present, holder_ids = _day(None, hold, wait)
    occ = {d: len(h) for d, h in zip(DEPARTMENTS, hold)}
    pool = data.draw(st.integers(sum(occ.values()), 4 * cap))
    beds = dict(occ)
    for _ in range(pool - sum(occ.values())):              # a random feasible allocation
        d = data.draw(st.sampled_from([d for d in DEPARTMENTS if beds[d] < cap]))
        beds[d] += 1
    asg = assign_beds(beds, present, holder_ids)
    pairs = bed_pairs(beds, cap, present, holder_ids, asg)
    holders = [p for p in present if p.patient_id in holder_ids]
    nonh = [p for p in present if p.patient_id not in holder_ids]
    mx = bed_tier_max(holders, nonh, pool, cap)
    gaps = {j: mx[j] - sum(1 for i in asg.in_bed if next(p for p in present if p.patient_id == i).complexity >= j)
            for j in LEVELS}
    assert all(g >= 0 for g in gaps.values())
    assert sum(p.severity for p in pairs) == sum(gaps.values())
    assert all(p.kind in ("displaced", "empty") for p in pairs)


@pytest.mark.slow
@PROPS
@given(dept_lists, dept_lists, st.integers(3, 8), st.data())
def test_pairing_equals_closed_form_shock_day(hold, wait, cap, data):
    """Required before any use on the stress variant (owner decision §11 #19)."""
    hold = [h[:cap] for h in hold]
    present, holder_ids = _day(None, hold, wait)
    occ = {d: len(h) for d, h in zip(DEPARTMENTS, hold)}
    total = sum(occ.values())
    if total == 0:
        return
    pool = data.draw(st.integers(0, total - 1))             # a shortfall: c = total - pool cuts
    c = total - pool
    cuts = {d: 0 for d in DEPARTMENTS}                      # a random exact cut (relaxed no-eviction)
    for _ in range(c):
        d = data.draw(st.sampled_from([d for d in DEPARTMENTS if occ[d] - cuts[d] > 0]))
        cuts[d] += 1
    beds = {d: occ[d] - cuts[d] for d in DEPARTMENTS}
    asg = assign_beds(beds, present, holder_ids)
    assert not asg.admitted
    pairs = bed_pairs(beds, cap, present, holder_ids, asg)
    holders = [p for p in present if p.patient_id in holder_ids]
    nonh = [p for p in present if p.patient_id not in holder_ids]
    mx = bed_tier_max(holders, nonh, pool, cap)
    lvl = {p.patient_id: p.complexity for p in present}
    gaps = {j: mx[j] - sum(1 for i in asg.in_bed if lvl[i] >= j) for j in LEVELS}
    assert all(g >= 0 for g in gaps.values())
    assert sum(p.severity for p in pairs) == sum(gaps.values())
    assert all(p.kind == "shock_cut" for p in pairs)


def test_pairing_by_hand_displaced_and_empty():
    # Cardiology: L3 waiting, 35 beds worth of room; Orthopedics admits an L1; Neurology keeps an empty bed
    ca3 = Patient("P000001", CA, 3, 1)
    ca2 = Patient("P000002", CA, 2, 1)
    or1 = Patient("P000003", OR, 1, 2)
    present = [ca3, ca2, or1]
    beds = {IM: 0, CA: 0, NE: 1, OR: 1}
    asg = assign_beds(beds, present, set())
    pairs = bed_pairs(beds, 40, present, set(), asg)
    got = sorted((p.kind, p.unserved_level, p.served_level) for p in pairs)
    assert got == [("displaced", 2, 1), ("empty", 3, 0)]     # L3 takes the lowest bed (empty), L2 the L1 bed
    assert sum(p.severity for p in pairs) == 4


def test_cap_blocked_overflow_is_not_a_violation():
    ca3 = Patient("P000001", CA, 3, 1)
    or1 = Patient("P000002", OR, 1, 1)
    beds = {IM: 0, CA: 2, NE: 0, OR: 1}
    holders = {Patient(f"P9{i:05d}", CA, 1, -5).patient_id for i in range(2)}
    present = [ca3, or1] + [Patient(f"P9{i:05d}", CA, 1, -5) for i in range(2)]
    asg = assign_beds(beds, present, holders)
    assert ca3.patient_id in asg.overflow
    assert bed_pairs(beds, 2, present, holders, asg) == []    # Cardiology at its cap of 2


# ============================================================================ B1 is an oracle on A1 and B2

@pytest.mark.slow
@PROPS
@given(dept_lists, dept_lists, st.integers(3, 8), st.data())
def test_b1_scores_zero_on_bed_pairs_and_f1(hold, wait, cap, data):
    hold = [h[:cap] for h in hold]
    present, holder_ids = _day(None, hold, wait)
    occ = sum(len(h) for h in hold)
    pool = data.draw(st.integers(0, 4 * cap))
    ctx = DayContext(5, tuple(present), frozenset(holder_ids), pool, 10, cap, ENV)
    beds, nurses = b1(None, None, ctx)
    res = simulate(beds, nurses, ctx)
    assert res.violations == []
    assert res.bed_pairs == []
    if occ <= pool:                                         # F1 inversions are defined on normal days
        room = {d: cap - beds[d] for d in DEPARTMENTS}
        for p in present:
            if p.patient_id in res.assignment.overflow and room[p.department] > 0:
                for i in res.assignment.admitted:
                    q = next(x for x in present if x.patient_id == i)
                    assert not (q.complexity == p.complexity and q.department != p.department
                                and q.arrival_day > p.arrival_day)


# ============================================================================ what-if

def test_whatif_reports_invalid_proposals_without_outcomes():
    p = Patient("P000001", IM, 2, 1)
    ctx = DayContext(1, (p,), frozenset({p.patient_id}), 4, 2, 40, ENV)
    res = simulate({IM: 0, CA: 4, NE: 0, OR: 0}, {IM: 2, CA: 0, NE: 0, OR: 0}, ctx)
    assert {v.code for v in res.violations} == {"EVICTION"}
    res2 = simulate({IM: 1.5, CA: 2.5, NE: 0, OR: 0}, {IM: 2, CA: 0, NE: 0, OR: 0}, ctx)
    assert res2.assignment is None


def test_whatif_outcomes_match_rules():
    pts = [Patient("P000001", IM, 3, 1), Patient("P000002", IM, 1, 1), Patient("P000003", CA, 2, 1)]
    ctx = DayContext(1, tuple(pts), frozenset(), 2, 1, 40, ENV)
    res = simulate({IM: 1, CA: 1, NE: 0, OR: 0}, {IM: 1, CA: 0, NE: 0, OR: 0}, ctx)
    assert res.violations == []
    assert res.overflow[IM] == {1: 1, 2: 0, 3: 0}
    assert res.shortage[CA][2] == F(7, 20)                  # Cardiology has no nurse
    assert res.nurse_tier_gaps[3] == 0                      # the one nurse covers IM's L3 (0.6) rather than CA's L2
    assert res.nurse_tier_gaps[2] == 0                      # tier 2: max(0.6, 0.35) = 0.6 achieved
    assert res.nurse_tier_gaps[1] == 0                      # tier 1: IM 0.8 -> min(1, 0.8) = 0.8 is the max
