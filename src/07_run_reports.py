"""Step 7: rebuild each agent run's report: per-day attempts, CHECKER reports matched against the audit, cost.

    uv run python src/07_run_reports.py [RUN ...]      # default: R1 R2 R3 STRESS1

Thin wrapper around `src.evaluation.run_report.build` (CHECKER-vs-audit matching: src/evaluation/checker_matching.py).
Writes results/analysis/recomputed/<run>/run_report.json and compares it with the committed
results/evaluations/<run>/run_report.json, which copy-back built.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.run_report import build  # noqa: E402
from src.utils.compare import report  # noqa: E402
from src.utils.paths import recomputed_dir  # noqa: E402

RUNS = ["R1", "R2", "R3", "STRESS1"]

if __name__ == "__main__":
    rows = []
    for run in sys.argv[1:] or RUNS:
        r = build(run)                                       # default output: results/analysis/recomputed/<run>/
        print(f"{run}: models {r['models_configured']}, session cost {r['session_cost_usd']}")
        rows.append((f"{run} run report", recomputed_dir(run) / "run_report.json",
                     ROOT / "results" / "evaluations" / run / "run_report.json"))
    sys.exit(report(rows))
