"""N1 nurse requirement, coverage rule C1 and nurse tier maxima (CLAUDE.md §10.D, PROJECT_SPEC.md §5.4,
EVALUATION_PLAN.md §3.2), in exact arithmetic.

N1 is implemented independently of src/data_generation/stats.py (Fraction of the decimal weights here,
integer hundredths there); the two are cross-checked in tests.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Sequence

from src.utils.constants import LEVELS


def weight_fractions(weights: dict) -> dict[int, Fraction]:
    """w_L1..w_L3 read as exact decimals."""
    return {k: Fraction(str(weights[f"w_L{k}"])) for k in LEVELS}


def requirement(n1: int, n2: int, n3: int, weights: dict) -> int:
    """ceil(w1*n1 + w2*n2 + w3*n3), with the weights read as exact decimals."""
    total = (Fraction(str(weights["w_L1"])) * n1 + Fraction(str(weights["w_L2"])) * n2
             + Fraction(str(weights["w_L3"])) * n3)
    return -((-total.numerator) // total.denominator)


def need_by_level(counts: dict[int, int], weights: dict) -> dict[int, Fraction]:
    """need_k = w_k * n_k for one department; `counts` maps level -> present patients (overflow included)."""
    w = weight_fractions(weights)
    return {k: w[k] * counts.get(k, 0) for k in LEVELS}


def coverage(nurses: int, need: dict[int, Fraction]) -> tuple[dict[int, Fraction], dict[int, Fraction]]:
    """Rule C1: N_d nurses cover L3 first, then L2, then L1. Returns (covered, shortage) by level."""
    remaining = Fraction(nurses)
    covered: dict[int, Fraction] = {}
    for k in sorted(LEVELS, reverse=True):
        covered[k] = min(need[k], remaining)
        remaining -= covered[k]
    shortage = {k: need[k] - covered[k] for k in LEVELS}
    return covered, shortage


def tier_need(need: dict[int, Fraction], j: int) -> Fraction:
    """a_j = sum of need at levels >= j."""
    return sum((need[k] for k in LEVELS if k >= j), Fraction(0))


def max_tier_coverage(pool: int, a: Sequence[Fraction]) -> Fraction:
    """max over integer N >= 0 with sum N = pool of sum_d min(N_d, a_d) (Decisions Log #46).

    Three cases: everything covered; every nurse covers a full unit; otherwise whole units first and
    the remaining nurses on the largest fractional parts."""
    a = [Fraction(x) for x in a]
    if pool >= sum(math.ceil(x) for x in a):
        return sum(a, Fraction(0))
    floors = sum(math.floor(x) for x in a)
    if pool <= floors:
        return Fraction(pool)
    fracs = sorted((x - math.floor(x) for x in a), reverse=True)
    return floors + sum(fracs[: pool - floors], Fraction(0))


def tier_gaps(nurses: dict[str, int], needs: dict[str, dict[int, Fraction]], pool: int) -> dict[int, Fraction]:
    """gapN_j = MaxN_j - achieved tier-j coverage, for j = 1..3 (EVALUATION_PLAN.md §3.2)."""
    out = {}
    for j in LEVELS:
        a = {d: tier_need(needs[d], j) for d in needs}
        achieved = sum((min(Fraction(nurses[d]), a[d]) for d in needs), Fraction(0))
        out[j] = max_tier_coverage(pool, list(a.values())) - achieved
    return out
