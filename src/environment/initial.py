"""Common initial allocation (CLAUDE.md §10.L, PROJECT_SPEC.md §5.2)."""

from __future__ import annotations

from src.utils.constants import DEPARTMENTS

from .allocation import largest_remainder


def initial_allocation(pool_beds: int, pool_nurses: int, census: dict[str, int],
                       requirement: dict[str, int], max_beds: int) -> tuple[dict[str, int], dict[str, int]]:
    """Beds LR(P_B(1), census_d(1), caps = max_beds); nurses LR(P_N(1), requirement_d(1))."""
    beds = largest_remainder(pool_beds, [census[d] for d in DEPARTMENTS], caps=[max_beds] * len(DEPARTMENTS))
    nurses = largest_remainder(pool_nurses, [requirement[d] for d in DEPARTMENTS])
    return dict(zip(DEPARTMENTS, beds)), dict(zip(DEPARTMENTS, nurses))
