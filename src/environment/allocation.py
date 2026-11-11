"""Largest-remainder apportionment LR(total, weights, caps) (PROJECT_SPEC.md §5.1).

Exact rational arithmetic, so fractional-part ties are real ties and go to department order.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Sequence


class InfeasibleError(ValueError):
    """Raised when the caps cannot hold the total (sum of caps < total)."""


def largest_remainder(total: int, weights: Sequence, caps: Sequence[int] | None = None) -> list[int]:
    n = len(weights)
    if total < 0:
        raise ValueError("total must be >= 0")
    if any(Fraction(w) < 0 for w in weights):
        raise ValueError("weights must be >= 0")
    cap = [math.inf] * n if caps is None else list(caps)
    if any(c < 0 for c in cap):
        raise ValueError("caps must be >= 0")
    if sum(cap) < total:
        raise InfeasibleError(f"sum of caps {sum(cap)} < total {total}")

    alloc = [0] * n
    remaining = total
    active = [i for i in range(n) if cap[i] > 0]
    while remaining > 0:
        w = {i: Fraction(weights[i]) for i in active}
        W = sum(w.values())
        if W == 0:                                    # step 1: equal weights if the weights sum to 0
            w = {i: Fraction(1) for i in active}
            W = Fraction(len(active))
        quota = {i: remaining * w[i] / W for i in active}
        floors = {i: math.floor(quota[i]) for i in active}
        leftover = 0
        for i in active:                              # step 2: floors, capped
            give = min(floors[i], cap[i] - alloc[i])
            alloc[i] += give
            leftover += floors[i] - give
        rounding = remaining - sum(floors.values())   # step 3: one unit each, largest fractions first
        for i in sorted(active, key=lambda i: (-(quota[i] - floors[i]), i)):
            if rounding == 0:
                break
            if alloc[i] < cap[i]:
                alloc[i] += 1
                rounding -= 1
        remaining = leftover + rounding               # step 4: redistribute what the caps left unplaced
        active = [i for i in active if alloc[i] < cap[i]]
        if remaining > 0 and not active:
            raise InfeasibleError("caps exhausted")   # unreachable given the sum-of-caps check
    return alloc
