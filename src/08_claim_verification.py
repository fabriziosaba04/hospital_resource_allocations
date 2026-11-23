"""Step 8: verify the ALLOCATOR's explanation claims one by one (EVALUATION_PLAN.md §4; owner decision §11 #48).

    uv run python src/08_claim_verification.py [RUN]      # default: R1 (the run whose claims were extracted)

Thin wrapper around `src.evaluation.claim_check.score`: each numeric claim in the committed extraction
(results/evaluations/<run>/explanation_claims_spec.json) is recomputed with the what-if engine on that day's
state, rebuilt from the run records, never read off the explanation. Writes
results/analysis/recomputed/<run>/explanation_claims.json and compares it with the committed file. The owner's
review of the verdicts is in results/evaluations/R1/owner_review/ (claim_accuracy_after_owner_review.json).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.claim_check import score  # noqa: E402
from src.utils.compare import report  # noqa: E402
from src.utils.paths import guard_write, recomputed_dir  # noqa: E402

if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "R1"
    out = score(run)
    print(json.dumps(out["summary"], indent=2))
    dst = guard_write(recomputed_dir(run))
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "explanation_claims.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    sys.exit(report([(f"{run} claims", dst / "explanation_claims.json",
                      ROOT / "results" / "evaluations" / run / "explanation_claims.json")]))
