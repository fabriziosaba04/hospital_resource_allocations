"""Fixed policy colours and figure style for Phase 3 (Decisions Log #136).

One colour per policy across every figure: R1-R3 in one hue family (three ordinal steps of the reference blue
ramp, dataviz skill references/palette.md), the baselines in three neutral greys. Greys have no chroma, so the
baselines also carry a hatch (secondary encoding), and every bar carries a direct value label.

`palette_report` is a Python port of the checks of the dataviz skill's scripts/validate_palette.js that apply
to a static PNG (same Machado-Oliveira-Fernandes 2009 severity-1.0 CVD matrices, OKLab Delta E x100, WCAG
contrast); node is not installed here, so the script itself could not be run.
"""

from __future__ import annotations

import math
from itertools import combinations

POLICY = {"R1": "#104281", "R2": "#2a78d6", "R3": "#86b6ef",        # blue ramp steps 650, 450, 250
          "B0": "#282822", "B1": "#70706a", "B2": "#e8e8e2"}          # neutral greys, dark -> light
HATCH = {"R1": "", "R2": "", "R3": "", "B0": "xx", "B1": "//", "B2": ".."}
DEPT = {"internal_medicine": "#2a78d6", "cardiology": "#eb6834", "neurology": "#1baf7a",
        "orthopedics": "#eda100"}    # reference slots 1-4 (pass adjacent pairs); departments are always named
#                                      on an axis or a panel title, so colour never carries their identity alone
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
DPI = 200

MACHADO = {"protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
                      [-0.003882, -0.048116, 1.051998]],
           "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
                      [-0.011820, 0.042940, 0.968881]],
           "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602],
                      [0.004733, 0.691367, 0.303900]]}


def _lin(h: str) -> list[float]:
    h = h.lstrip("#")
    s = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in s]


def _oklab(rgb: list[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _sim(h: str, kind: str | None) -> list[float]:
    x = _lin(h)
    if kind is None:
        return x
    M = MACHADO[kind]
    return [max(0.0, min(1.0, sum(M[i][j] * x[j] for j in range(3)))) for i in range(3)]


def delta_e(a: str, b: str, kind: str | None = None) -> float:
    p, q = _oklab(_sim(a, kind)), _oklab(_sim(b, kind))
    return 100 * math.dist(p, q)


def contrast(a: str, b: str) -> float:
    lum = lambda h: sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), _lin(h)))  # noqa: E731
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def palette_report(colors: dict[str, str] = POLICY, surface: str = SURFACE) -> dict:
    """Worst pair over all pairs: unsimulated Delta E (floor 15), min(protan, deutan) Delta E (target 8,
    floor 6 with secondary encoding), tritan for information; contrast of each colour against the surface."""
    pairs = []
    for (n1, c1), (n2, c2) in combinations(colors.items(), 2):
        pairs.append({"pair": f"{n1}-{n2}", "normal": round(delta_e(c1, c2), 1),
                      "cvd": round(min(delta_e(c1, c2, "protan"), delta_e(c1, c2, "deutan")), 1),
                      "tritan": round(delta_e(c1, c2, "tritan"), 1)})
    return {"worst_normal": min(pairs, key=lambda p: p["normal"]),
            "worst_cvd": min(pairs, key=lambda p: p["cvd"]),
            "contrast": {n: round(contrast(c, surface), 2) for n, c in colors.items()},
            "pairs": pairs}
