"""N1 nurse requirement (CLAUDE.md §10.D, PROJECT_SPEC.md §5.4), in exact arithmetic.

Implemented independently of src/data_generation/stats.py (Fraction of the decimal weights here,
integer hundredths there); the two are cross-checked in tests.
"""

from __future__ import annotations

from fractions import Fraction


def requirement(n1: int, n2: int, n3: int, weights: dict) -> int:
    """ceil(w1*n1 + w2*n2 + w3*n3), with the weights read as exact decimals."""
    total = (Fraction(str(weights["w_L1"])) * n1 + Fraction(str(weights["w_L2"])) * n2
             + Fraction(str(weights["w_L3"])) * n3)
    return -((-total.numerator) // total.denominator)
