"""Baselines B0, B1, B2 (CLAUDE.md §10.L, PROJECT_SPEC.md §6). Deterministic, built only from the
environment functions, so they face exactly the agent's environment."""

from __future__ import annotations

import math
from fractions import Fraction

from src.environment.allocation import largest_remainder
from src.environment.nurses import requirement as n1_requirement
from src.environment.repair import repair_beds, repair_nurses
from src.environment.types import assign_order_key, cut_order_key
from src.environment.whatif import DayContext
from src.utils.constants import DEPARTMENTS, LEVELS


def _requirements(ctx: DayContext) -> dict[str, int]:
    c = ctx.counts()
    return {d: n1_requirement(c[d][1], c[d][2], c[d][3], ctx.weights) for d in DEPARTMENTS}


def _shock_floors(ctx: DayContext) -> dict[str, int]:
    """B_d = O_d, minus the hospital-wide cut of §5.7 step 2 if sum O_d > P_B."""
    occ = ctx.occupied
    c = sum(occ.values()) - ctx.pool_beds
    floors = dict(occ)
    if c > 0:
        for p in sorted(ctx.holders, key=cut_order_key)[:c]:
            floors[p.department] -= 1
    return floors


def b0(prev_beds, prev_nurses, ctx: DayContext):
    beds, _ = repair_beds(prev_beds, ctx.pool_beds, ctx.max_beds, ctx.holders)
    return beds, repair_nurses(prev_nurses, ctx.pool_nurses, _requirements(ctx))


def b1(prev_beds, prev_nurses, ctx: DayContext):
    # beds
    beds = _shock_floors(ctx)
    m = ctx.pool_beds - sum(beds.values())
    if m > 0:
        queue = sorted((p for p in ctx.present if p.patient_id not in ctx.holder_ids), key=assign_order_key)
        for p in queue:
            if m == 0:
                break
            if beds[p.department] < ctx.max_beds:
                beds[p.department] += 1
                m -= 1
        if m > 0:
            census = {d: 0 for d in DEPARTMENTS}
            for p in ctx.present:
                census[p.department] += 1
            add = largest_remainder(m, [census[d] for d in DEPARTMENTS],
                                    caps=[ctx.max_beds - beds[d] for d in DEPARTMENTS])
            beds = {d: beds[d] + a for d, a in zip(DEPARTMENTS, add)}
    # nurses: incremental integer need by tier, L3 first
    needs = ctx.needs()
    nurses = {d: 0 for d in DEPARTMENTS}
    remaining = ctx.pool_nurses
    for k in sorted(LEVELS, reverse=True):
        inc = {}
        for d in DEPARTMENTS:
            upto = sum((needs[d][j] for j in LEVELS if j >= k), Fraction(0))
            above = sum((needs[d][j] for j in LEVELS if j > k), Fraction(0))
            inc[d] = math.ceil(upto) - math.ceil(above)
        if sum(inc.values()) <= remaining:
            for d in DEPARTMENTS:
                nurses[d] += inc[d]
            remaining -= sum(inc.values())
        else:
            give = largest_remainder(remaining, [inc[d] for d in DEPARTMENTS], caps=[inc[d] for d in DEPARTMENTS])
            for d, g in zip(DEPARTMENTS, give):
                nurses[d] += g
            remaining = 0
            break
    if remaining > 0:
        req = _requirements(ctx)
        give = largest_remainder(remaining, [req[d] for d in DEPARTMENTS])
        for d, g in zip(DEPARTMENTS, give):
            nurses[d] += g
    return beds, nurses


def b2(prev_beds, prev_nurses, ctx: DayContext):
    census = {d: 0 for d in DEPARTMENTS}
    for p in ctx.present:
        census[p.department] += 1
    target = dict(zip(DEPARTMENTS, largest_remainder(ctx.pool_beds, [census[d] for d in DEPARTMENTS],
                                                     caps=[ctx.max_beds] * 4)))
    floors = _shock_floors(ctx)
    r = ctx.pool_beds - sum(floors.values())
    u = [max(0, target[d] - floors[d]) for d in DEPARTMENTS]
    weights = u if sum(u) > 0 else [census[d] for d in DEPARTMENTS]
    add = largest_remainder(r, weights, caps=[ctx.max_beds - floors[d] for d in DEPARTMENTS])
    beds = {d: floors[d] + a for d, a in zip(DEPARTMENTS, add)}
    req = _requirements(ctx)
    nurses = dict(zip(DEPARTMENTS, largest_remainder(ctx.pool_nurses, [req[d] for d in DEPARTMENTS])))
    return beds, nurses


BASELINES = {"B0": b0, "B1": b1, "B2": b2}
