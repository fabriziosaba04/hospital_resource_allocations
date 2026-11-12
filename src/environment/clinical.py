"""Clinical-priority violation detector for beds: the pairing rule (CLAUDE.md §10.G, EVALUATION_PLAN.md §3.1).

Shared by the what-if and the deterministic audit. The audit cross-checks its total against its own
closed form (src/evaluation/audit.py), so the two are independent implementations.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.constants import DEPARTMENTS

from .bed_assignment import BedAssignment
from .types import Patient, assign_order_key, cut_order_key


@dataclass(frozen=True)
class BedPair:
    kind: str                 # "displaced", "empty" or "shock_cut"
    unserved_id: str          # overflow patient (normal day) or cut holder (shock day)
    unserved_department: str
    unserved_level: int
    served_id: str | None     # the patient served in their place; None for an empty bed
    served_department: str
    served_level: int         # 0 for an empty bed

    @property
    def severity(self) -> int:
        return self.unserved_level - self.served_level


def bed_pairs(beds: dict[str, int], max_beds: int, present: list[Patient], holder_ids: set[str],
              assignment: BedAssignment) -> list[BedPair]:
    by_id = {p.patient_id: p for p in present}
    holders = [p for p in present if p.patient_id in holder_ids]
    occupied = {d: 0 for d in DEPARTMENTS}
    for p in holders:
        occupied[p.department] += 1
    pairs: list[BedPair] = []

    if sum(occupied.values()) > sum(beds.values()):                     # shock day
        cut = sorted((by_id[i] for i in assignment.evicted), key=assign_order_key)    # highest level first
        kept = sorted((p for p in holders if p.patient_id not in assignment.evicted), key=cut_order_key)
        used = [False] * len(kept)
        for u in cut:
            for i, s in enumerate(kept):
                if not used[i] and s.department != u.department and s.complexity < u.complexity:
                    used[i] = True
                    pairs.append(BedPair("shock_cut", u.patient_id, u.department, u.complexity,
                                         s.patient_id, s.department, s.complexity))
                    break
        return pairs

    # normal day: movable beds serve admitted non-holders, or stay empty (level 0)
    served: list[tuple[int, str, str | None]] = []      # (level, department, patient_id)
    for d in DEPARTMENTS:
        adm = [by_id[i] for i in assignment.admitted if by_id[i].department == d]
        served += [(p.complexity, d, p.patient_id) for p in adm]
        served += [(0, d, None)] * (beds[d] - occupied[d] - len(adm))
    served.sort(key=lambda x: (x[0], DEPARTMENTS.index(x[1]), x[2] or ""))
    unserved = sorted((by_id[i] for i in assignment.overflow), key=assign_order_key)
    room = {d: max_beds - beds[d] for d in DEPARTMENTS}
    used = [False] * len(served)
    for u in unserved:
        if room[u.department] <= 0:
            continue
        for i, (lvl, d2, pid) in enumerate(served):
            if not used[i] and d2 != u.department and lvl < u.complexity:
                used[i] = True
                room[u.department] -= 1
                pairs.append(BedPair("empty" if pid is None else "displaced", u.patient_id, u.department,
                                     u.complexity, pid, d2, lvl))
                break
    return pairs
