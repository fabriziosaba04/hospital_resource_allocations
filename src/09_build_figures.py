"""Step 9: build the static figures from the run records and the datasets (owner decision §11 #49).

    uv run python src/09_build_figures.py

Thin wrapper around `src.evaluation.figures.build`. The audit and the metrics behind every figure are recomputed,
never taken from an agent, so the figures show recorded decisions and invent no movements. Outputs:
results/figures/seed20261107/ (B0-B2, R1-R3) and results/figures/seed20261107_stress/ (B0-B2, STRESS1).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.figures import build  # noqa: E402

SETS = {"seed20261107": ["B0-seed20261107", "B1-seed20261107", "B2-seed20261107", "R1", "R2", "R3"],
        "seed20261107_stress": ["B0-seed20261107_stress", "B1-seed20261107_stress", "B2-seed20261107_stress",
                                "STRESS1"]}

if __name__ == "__main__":
    bad = 0
    for ds, runs in SETS.items():
        out = build(ds, runs)                                # default output: results/figures/<dataset>/
        problems = {r: p for r, p in out["record_field_problems"].items() if p}
        bad += bool(problems)
        print(json.dumps({"dataset": ds, "out": str(Path(out["out"]).relative_to(ROOT)),
                          "record_field_problems": problems}, indent=2))
    sys.exit(1 if bad else 0)
