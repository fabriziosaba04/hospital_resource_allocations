"""Step 8: verify the ALLOCATOR's explanation claims one by one (EVALUATION_PLAN.md §4; owner decision §11 #48),
then recompute the owner's review of them (§4 item 7; §11 #61-#69).

    uv run python src/08_claim_verification.py [RUN]      # default: R1 (the run whose claims were extracted)

1. Thin wrapper around `src.evaluation.claim_check.score`: each numeric claim in the committed extraction
   (results/evaluations/<run>/explanation_claims_spec.json) is recomputed with the what-if engine on that day's
   state, rebuilt from the run records, never read off the explanation. Writes
   results/analysis/recomputed/<run>/explanation_claims.json and compares it with the committed file.
2. Owner review (Decisions Log #127): the nine owner-review modules run on the committed run folder and the
   committed owner input tables, and write to results/analysis/recomputed/<run>/{owner_extraction,owner_review}/
   (never into the frozen run folder). Every generated file is compared BYTE FOR BYTE with the committed one,
   and the set of generated files must equal the committed set minus the owner input tables. These files carry
   the item-7a recall, the adjudication counts and the claim accuracy before and after the owner review.
"""
import shutil
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import (adjudication_recall, adjudication_view, claim_review, decisions_ab,  # noqa: E402
                            owner_claims, owner_review_counts, owner_verdicts, rubric_check_view, unverifiable_view)
from src.evaluation.claim_check import score  # noqa: E402
from src.utils.compare import report  # noqa: E402
from src.utils.paths import guard_write, long_path, recomputed_dir  # noqa: E402

# owner input tables: committed by hand, read by the modules, never generated (owner_inputs.py, §11 #62)
OWNER_INPUTS = {"owner_extraction": {"owner_claims_d03_d08_d18.csv", "mapping_quantity.csv", "row_overrides.csv",
                                     "owner_adjudication_causes.csv", "owner_verdicts_nonmech.csv",
                                     "owner_universe_overrides.csv"},
                "owner_review": {"owner_review_wrong.csv", "owner_review_unverifiable.csv"}}


def owner_review(run: str) -> int:
    out, committed = guard_write(recomputed_dir(run)), ROOT / "results" / "evaluations" / run
    for sub in OWNER_INPUTS:                              # start empty: a stale file would hide a missing output
        if long_path(out / sub).exists():
            shutil.rmtree(long_path(out / sub))
    owner_claims.main(run, out_dir=out)                   # also re-applies owner_verdicts
    claim_review.main(run, out_dir=out)
    owner_verdicts.main(run, out_dir=out)
    decisions_ab.main(run, out_dir=out)
    adjudication_recall.main(run, out_dir=out)
    adjudication_view.main(run, out_dir=out)
    rubric_check_view.main(run, out_dir=out)
    unverifiable_view.main(run, out_dir=out)
    owner_review_counts.main(run, out_dir=out)
    rows, bad = [], 0
    for sub, inputs in OWNER_INPUTS.items():
        made = {p.name for p in long_path(out / sub).iterdir()}
        expected = {p.name for p in long_path(committed / sub).iterdir()} - inputs
        if made != expected:
            bad += 1
            print(f"  {sub}: generated files differ from the committed set: "
                  f"missing {sorted(expected - made)}, extra {sorted(made - expected)}")
        rows += [(f"{run} {sub}/{n}", out / sub / n, committed / sub / n) for n in sorted(made & expected)]
    return report(rows, exact=True) or (1 if bad else 0)


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "R1"
    out = score(run)
    print(json.dumps(out["summary"], indent=2))
    dst = guard_write(recomputed_dir(run))
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "explanation_claims.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    rc = report([(f"{run} claims", dst / "explanation_claims.json",
                  ROOT / "results" / "evaluations" / run / "explanation_claims.json")])
    if long_path(ROOT / "results" / "evaluations" / run / "owner_review").exists():
        print("owner review:")
        rc = owner_review(run) or rc
    sys.exit(rc)
