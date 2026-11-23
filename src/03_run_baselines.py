"""Step 3: run the baselines B0-B2 on the four frozen datasets, audit them, and rebuild the headroom table.

    uv run python src/03_run_baselines.py

Thin wrapper around `python -m src.evaluation`. Outputs go to results/analysis/recomputed/baselines/ (never over
the committed baselines) and are compared with results/{allocations,evaluations}/B?-<dataset>/ and
results/evaluations/headroom.json, ignoring the `created_at` timestamps.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.__main__ import BASELINES, MAIN, STRESS, main  # noqa: E402
from src.utils.compare import report  # noqa: E402

if __name__ == "__main__":
    out = ROOT / "results" / "analysis" / "recomputed" / "baselines"
    if main(["--out", str(out)]) != 0:
        sys.exit(1)
    res = ROOT / "results"
    rows = []
    for ds in MAIN + STRESS:
        for b in BASELINES:
            run = f"{b}-{ds}"
            for kind, name in (("allocations", "allocation_state.jsonl"), ("allocations", "bed_assignment_state.jsonl"),
                               ("evaluations", "deterministic_audit.jsonl"), ("evaluations", "metrics.json")):
                rows.append((f"{run} {name}", out / kind / run / name, res / kind / run / name))
    rows.append(("headroom", out / "evaluations" / "headroom.json", res / "evaluations" / "headroom.json"))
    sys.exit(report(rows))
