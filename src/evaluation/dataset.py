"""Read-only access to a frozen dataset for the baseline runner and the deterministic audit.

Reads the three CSV tables and `environment_config` only. It never opens `generation_config`
(PROJECT_SPEC.md §0: nothing in src/evaluation/ may embed or read generation parameters).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from src.environment.types import Patient

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RegistryRow:
    patient: Patient
    discharge_day: int


@dataclass
class Dataset:
    dataset_id: str
    registry: list[RegistryRow]
    pool_beds: dict[int, int]
    pool_nurses: dict[int, int]
    env: dict
    horizon: int
    _present_cache: dict[int, list[Patient]] = field(default_factory=dict, repr=False)

    @property
    def max_beds(self) -> int:
        return int(self.env["max_beds"])

    def present(self, day: int) -> list[Patient]:
        """Presence convention: arrival_day <= day < discharge_day."""
        if day not in self._present_cache:
            self._present_cache[day] = [r.patient for r in self.registry
                                        if r.patient.arrival_day <= day < r.discharge_day]
        return self._present_cache[day]


def load_dataset(dataset_id: str, root: Path = ROOT) -> Dataset:
    raw = root / "data" / "raw" / dataset_id
    with open(raw / "patient_registry.csv", newline="", encoding="utf-8") as f:
        registry = [RegistryRow(Patient(r["patient_id"], r["department"], int(r["complexity"]),
                                        int(r["arrival_day"])), int(r["discharge_day"]))
                    for r in csv.DictReader(f)]
    pool_beds, pool_nurses = {}, {}
    with open(raw / "hospital_resources_daily.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pool_beds[int(r["day"])] = int(r["total_beds"])
            pool_nurses[int(r["day"])] = int(r["total_nurses"])
    env = json.loads((root / "data" / "metadata" / dataset_id / "environment_config.json").read_text(encoding="utf-8"))
    return Dataset(dataset_id, registry, pool_beds, pool_nurses, env, max(pool_beds))
