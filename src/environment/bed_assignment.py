"""Intra-department bed assignment (CLAUDE.md §10.F, PROJECT_SPEC.md §5.3)."""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.constants import DEPARTMENTS

from .types import Patient, assign_order_key, cut_order_key


@dataclass(frozen=True)
class BedAssignment:
    in_bed: frozenset[str]        # patient_ids holding a bed after the allocation takes effect
    overflow: frozenset[str]      # patient_ids present without a bed
    evicted: frozenset[str]       # previous holders who lost their bed (shock cut only)
    admitted: frozenset[str]      # non-holders who received a free bed


def assign_beds(beds: dict[str, int], present: list[Patient], holder_ids: set[str]) -> BedAssignment:
    """`present`: every patient present on day t. `holder_ids`: patients who held a bed at the
    end of t-1 (only those still present count). Returns the day-t assignment."""
    in_bed: set[str] = set()
    evicted: set[str] = set()
    admitted: set[str] = set()
    for dept in DEPARTMENTS:
        pts = [p for p in present if p.department == dept]
        holders = sorted((p for p in pts if p.patient_id in holder_ids), key=cut_order_key)
        others = sorted((p for p in pts if p.patient_id not in holder_ids), key=assign_order_key)
        b = beds[dept]
        n_cut = max(0, len(holders) - b)              # step 2: shock cut, lowest first
        evicted |= {p.patient_id for p in holders[:n_cut]}
        kept = holders[n_cut:]
        free = max(0, b - len(kept))                  # step 3: free beds, highest level first
        admitted |= {p.patient_id for p in others[:free]}
        in_bed |= {p.patient_id for p in kept} | {p.patient_id for p in others[:free]}
    overflow = {p.patient_id for p in present} - in_bed
    return BedAssignment(frozenset(in_bed), frozenset(overflow), frozenset(evicted), frozenset(admitted))
