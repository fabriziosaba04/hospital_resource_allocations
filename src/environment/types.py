"""Shared types and orderings for the environment rules."""

from __future__ import annotations

from typing import NamedTuple

from src.utils.constants import DEPARTMENTS


class Patient(NamedTuple):
    patient_id: str
    department: str
    complexity: int
    arrival_day: int


def id_number(patient_id: str) -> int:
    return int(patient_id[1:])


def cut_order_key(p: Patient) -> tuple:
    """Order in which occupied beds are cut (§5.3 step 2, §5.7): complexity ascending,
    arrival_day descending, patient_id descending. The first element is cut first."""
    return (p.complexity, -p.arrival_day, -id_number(p.patient_id))


def assign_order_key(p: Patient) -> tuple:
    """Order in which free beds are given (§5.3 step 3): complexity descending,
    arrival_day ascending, patient_id ascending."""
    return (-p.complexity, p.arrival_day, id_number(p.patient_id))


def occupied_by_department(holders: list[Patient]) -> dict[str, int]:
    out = {d: 0 for d in DEPARTMENTS}
    for p in holders:
        out[p.department] += 1
    return out
