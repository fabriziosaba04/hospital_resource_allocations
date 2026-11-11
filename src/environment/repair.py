"""Failure repair rule (AGENTS.md §10, PROJECT_SPEC.md §5.7)."""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.constants import DEPARTMENTS

from .allocation import largest_remainder
from .types import Patient, cut_order_key, occupied_by_department


@dataclass(frozen=True)
class RepairResult:
    beds: dict[str, int]
    nurses: dict[str, int]
    cut_patient_ids: tuple[str, ...]     # holders whose beds are cut, in hospital-wide cut order


def _vec(d: dict) -> list:
    return [d[k] for k in DEPARTMENTS]


def _dict(v: list) -> dict:
    return dict(zip(DEPARTMENTS, v))


def repair_nurses(prev: dict[str, int], pool: int, requirement: dict[str, int]) -> dict[str, int]:
    n = _vec(prev)
    delta = pool - sum(n)
    if delta >= 0:
        weights = n if any(n) else _vec(requirement)
        add = largest_remainder(delta, weights)
        return _dict([a + b for a, b in zip(n, add)])
    sub = largest_remainder(-delta, n, caps=n)
    return _dict([a - b for a, b in zip(n, sub)])


def repair_beds(prev: dict[str, int], pool: int, max_beds: int,
                holders: list[Patient]) -> tuple[dict[str, int], tuple[str, ...]]:
    """`holders`: patients holding a bed at the end of t-1 who are still present on t (they define O_d(t))."""
    b = _vec(prev)
    occ = _vec(occupied_by_department(holders))
    delta = pool - sum(b)
    if delta > 0:
        add = largest_remainder(delta, b, caps=[max_beds - x for x in b])
        return _dict([x + y for x, y in zip(b, add)]), ()
    if delta == 0:
        return _dict(b), ()
    need = -delta
    free = [max(0, x - o) for x, o in zip(b, occ)]
    r = min(need, sum(free))                          # 1. remove free beds first
    sub = largest_remainder(r, free, caps=free)
    b = [x - y for x, y in zip(b, sub)]
    c = need - r                                      # 2. then cut occupied beds hospital-wide
    cut = sorted(holders, key=cut_order_key)[:c]
    for p in cut:
        b[DEPARTMENTS.index(p.department)] -= 1
    return _dict(b), tuple(p.patient_id for p in cut)


def repair(prev_beds, prev_nurses, pool_beds, pool_nurses, max_beds, holders, requirement) -> RepairResult:
    beds, cut = repair_beds(prev_beds, pool_beds, max_beds, holders)
    return RepairResult(beds, repair_nurses(prev_nurses, pool_nurses, requirement), cut)
