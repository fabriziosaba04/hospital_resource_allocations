"""What-if computation (PROJECT_SPEC.md §5.6): day-t outcomes of a proposal, in memory, no writes."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from src.utils.constants import DEPARTMENTS, LEVELS

from .bed_assignment import BedAssignment, assign_beds
from .clinical import BedPair, bed_pairs
from .nurses import coverage, need_by_level, tier_gaps
from .types import Patient, occupied_by_department
from .validator import Violation, validate


@dataclass(frozen=True)
class DayContext:
    day: int
    present: tuple[Patient, ...]
    holder_ids: frozenset[str]
    pool_beds: int
    pool_nurses: int
    max_beds: int
    weights: dict

    @property
    def holders(self) -> list[Patient]:
        return [p for p in self.present if p.patient_id in self.holder_ids]

    @property
    def occupied(self) -> dict[str, int]:
        return occupied_by_department(self.holders)

    def counts(self) -> dict[str, dict[int, int]]:
        c = {d: {k: 0 for k in LEVELS} for d in DEPARTMENTS}
        for p in self.present:
            c[p.department][p.complexity] += 1
        return c

    def needs(self) -> dict[str, dict[int, Fraction]]:
        return {d: need_by_level(cnt, self.weights) for d, cnt in self.counts().items()}


@dataclass(frozen=True)
class WhatIfResult:
    violations: list[Violation]
    assignment: BedAssignment | None
    overflow: dict[str, dict[int, int]]
    covered: dict[str, dict[int, Fraction]]
    shortage: dict[str, dict[int, Fraction]]
    bed_pairs: list[BedPair]
    nurse_tier_gaps: dict[int, Fraction]


def simulate(beds: dict[str, int], nurses: dict[str, int], ctx: DayContext) -> WhatIfResult:
    violations = validate(beds, nurses, ctx.pool_beds, ctx.pool_nurses, ctx.max_beds, ctx.occupied)
    if any(v.code in ("BOUNDS", "INTEGRALITY") for v in violations):
        return WhatIfResult(violations, None, {}, {}, {}, [], {})
    present = list(ctx.present)
    asg = assign_beds(beds, present, set(ctx.holder_ids))
    overflow = {d: {k: 0 for k in LEVELS} for d in DEPARTMENTS}
    for p in present:
        if p.patient_id in asg.overflow:
            overflow[p.department][p.complexity] += 1
    needs = ctx.needs()
    covered, shortage = {}, {}
    for d in DEPARTMENTS:
        covered[d], shortage[d] = coverage(nurses[d], needs[d])
    pairs = bed_pairs(beds, ctx.max_beds, present, set(ctx.holder_ids), asg) if not violations else []
    gaps = tier_gaps(nurses, needs, ctx.pool_nurses) if sum(nurses.values()) == ctx.pool_nurses else {}
    return WhatIfResult(violations, asg, overflow, covered, shortage, pairs, gaps)
