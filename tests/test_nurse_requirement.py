"""Hand-computed N1 requirements (CLAUDE.md §10.D): guards against both implementations sharing
the same misreading of the spec. Every expected value below was computed by hand, not by code.

N1: requirement_d = ceil( sum over present patients p in d of w(level_p) ), w = 0.20 / 0.35 / 0.60.
Rounding is applied PER DEPARTMENT; the hospital total is the sum of the rounded department values.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_generation.stats import compute_stats, n1_requirement as stats_n1
from src.environment.nurses import requirement as env_n1

W = {"w_L1": 0.20, "w_L2": 0.35, "w_L3": 0.60, "max_beds": 40}

# (n_L1, n_L2, n_L3) -> hand computation -> expected requirement
HAND = [
    ((7, 5, 3), "1.40 + 1.75 + 1.80 = 4.95 -> 5", 5),
    ((0, 1, 0), "0.35 -> 1", 1),
    ((1, 0, 0), "0.20 -> 1", 1),
    ((3, 4, 5), "0.60 + 1.40 + 3.00 = 5.00 exactly -> 5", 5),
    ((0, 20, 0), "7.00 exactly -> 7", 7),
    ((12, 0, 1), "2.40 + 0.60 = 3.00 exactly -> 3 (floating point gives 3.0000000000000004 -> 4)", 3),
    ((24, 0, 2), "4.80 + 1.20 = 6.00 exactly -> 6 (floating point gives 6.000000000000001 -> 7)", 6),
    ((5, 0, 0), "1.00 exactly -> 1", 1),
    ((0, 0, 0), "0 -> 0", 0),
    ((10, 10, 10), "2.0 + 3.5 + 6.0 = 11.5 -> 12", 12),
]


@pytest.mark.parametrize("counts,why,expected", HAND, ids=[w for _, w, _ in HAND])
def test_department_requirement_by_hand(counts, why, expected):
    assert env_n1(*counts, W) == expected
    assert int(stats_n1(*counts, W)) == expected


def test_hospital_total_rounds_per_department():
    """Departments (7,5,3), (0,1,0), (1,0,0), (3,4,5) -> 5 + 1 + 1 + 5 = 12.
    (Floating point is a further hazard, covered by the (12,0,1) and (24,0,2) cases.)
    Rounding the pooled sum instead would give ceil(4.95 + 0.35 + 0.20 + 5.00) = ceil(10.5) = 11."""
    mixes = {"internal_medicine": (7, 5, 3), "cardiology": (0, 1, 0), "neurology": (1, 0, 0), "orthopedics": (3, 4, 5)}
    demand = pd.DataFrame([
        {"day": 1, "department": d, "arrivals": 0, "discharges": 0,
         "census_L1": c[0], "census_L2": c[1], "census_L3": c[2]} for d, c in mixes.items()
    ])
    resources = pd.DataFrame([{"day": 1, "total_beds": 96, "total_nurses": 37, "external_event": ""}])
    registry = pd.DataFrame({"patient_id": [f"P{i:06d}" for i in range(1, 7)], "department": ["cardiology"] * 6,
                             "complexity": [1, 1, 2, 2, 3, 3], "arrival_day": [0] * 6, "discharge_day": [3, 4, 5, 6, 8, 9]})
    st = compute_stats(resources, demand, registry, W)
    assert st["n1_requirement"]["mean"] == 12
    assert sum(env_n1(*c, W) for c in mixes.values()) == 12
