"""Step 6: recompute the deterministic audit and the metrics of the agent runs without the agent.

    uv run python src/06_audit_and_metrics.py [RUN ...]      # default: R1 R2 R3 STRESS1

Thin wrapper around `src.evaluation.metrics.evaluate_run`, which re-implements the hard constraints, N1, nurse
coverage and the bed-assignment replay independently of the environment (src/evaluation/audit.py) and uses no LLM
output. Writes results/analysis/recomputed/<run>/ (deterministic_audit.jsonl, metrics.json) and compares the audit
with the committed results/evaluations/<run>/deterministic_audit.jsonl, ignoring `created_at`.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.dataset import load_dataset  # noqa: E402
from src.evaluation.metrics import evaluate_run  # noqa: E402
from src.utils.compare import report  # noqa: E402
from src.utils.paths import recomputed_dir  # noqa: E402

RUNS = ["R1", "R2", "R3", "STRESS1"]

if __name__ == "__main__":
    rows = []
    for run in sys.argv[1:] or RUNS:
        alloc = ROOT / "results" / "allocations" / run
        ds = load_dataset(json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))["dataset_id"])
        m = evaluate_run(ds, alloc)                         # default output: results/analysis/recomputed/<run>/
        print(f"{run}: gate D passed = {m['D']['gate_passed']}")
        name = "deterministic_audit.jsonl"
        rows.append((f"{run} audit", recomputed_dir(run) / name, ROOT / "results" / "evaluations" / run / name))
    sys.exit(report(rows))
