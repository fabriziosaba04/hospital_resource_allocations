"""Hard-constraint validator (CLAUDE.md §10.E, PROJECT_SPEC.md §5.5)."""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.constants import DEPARTMENTS


@dataclass(frozen=True)
class Violation:
    code: str      # CONSERVATION_BEDS, CONSERVATION_NURSES, BOUNDS, INTEGRALITY, EVICTION, SHOCK_OVERCUT
    message: str


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate(beds: dict, nurses: dict, pool_beds: int, pool_nurses: int, max_beds: int,
             occupied: dict[str, int]) -> list[Violation]:
    """`occupied` is O_d(t): beds in d still held by patients who held one at the end of t-1.
    An empty list means the proposal is valid."""
    v: list[Violation] = []
    for name, alloc in (("beds", beds), ("nurses", nurses)):
        if set(alloc) != set(DEPARTMENTS):
            v.append(Violation("BOUNDS", f"{name}: departments {sorted(alloc)} != {sorted(DEPARTMENTS)}"))
    if v:
        return v
    for name, alloc in (("beds", beds), ("nurses", nurses)):
        for d in DEPARTMENTS:
            if not _is_int(alloc[d]):
                v.append(Violation("INTEGRALITY", f"{name}[{d}] = {alloc[d]!r} is not an integer"))
    if v:
        return v
    if sum(beds.values()) != pool_beds:
        v.append(Violation("CONSERVATION_BEDS", f"sum of beds {sum(beds.values())} != pool {pool_beds}"))
    if sum(nurses.values()) != pool_nurses:
        v.append(Violation("CONSERVATION_NURSES", f"sum of nurses {sum(nurses.values())} != pool {pool_nurses}"))
    for d in DEPARTMENTS:
        if not 0 <= beds[d] <= max_beds:
            v.append(Violation("BOUNDS", f"beds[{d}] = {beds[d]} outside [0, {max_beds}]"))
        if nurses[d] < 0:
            v.append(Violation("BOUNDS", f"nurses[{d}] = {nurses[d]} < 0"))

    total_occupied = sum(occupied[d] for d in DEPARTMENTS)
    cuts = {d: max(0, occupied[d] - beds[d]) for d in DEPARTMENTS}
    total_cut = sum(cuts.values())
    shortfall = max(0, total_occupied - pool_beds)
    if shortfall == 0:
        for d in DEPARTMENTS:
            if cuts[d] > 0:
                v.append(Violation("EVICTION",
                                   f"beds[{d}] = {beds[d]} < occupied {occupied[d]} with no shock shortfall"))
    elif total_cut > shortfall:
        v.append(Violation("SHOCK_OVERCUT",
                           f"{total_cut} occupied beds cut, but the shock shortfall is only {shortfall}"))
    return v
