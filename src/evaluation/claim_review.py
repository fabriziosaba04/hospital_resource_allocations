"""Owner review lists (EVALUATION_PLAN.md §4 item 7b-c): every claim the recomputation marks wrong, and every
claim marked unverifiable, from `<eval>/explanation_claims.json`. No CHECKER matching.

    uv run python -m src.evaluation.claim_review R1 [--out DIR]   # <out> = DIR, default results/analysis/recomputed/R1/ (Log #127)

Wrong claims carry a `tier` (owner request 2026-11-18; no verdict changes):
  wrong_only_primary   a bare "spare" / "free" claim, wrong under the strict reading, correct under the rival
  wrong_both_readings  a bare "spare" / "free" claim, wrong under both readings
  no_spare_free_term   any other wrong claim (no rival reading of spare / free applies)
The counts and ids are also written to `owner_review/wrong_claims_tiers.json`.
`owner_verdict` / `owner_comment` come from the owner input tables `owner_review_wrong.csv` and
`owner_review_unverifiable.csv` (owner_inputs.py), which this module reads and never writes.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from .dataset import ROOT
from .owner_claims import encoding
from src.utils.paths import guard_write, long_path, review_out_dir

COLUMNS = ["id", "day", "field", "text", "category", "basis", "encoding", "computed", "computed_compare",
           "rubric_term", "verdict_alternative", "computed_alternative", "tier", "note", "owner_verdict",
           "owner_comment"]
SPARE_FREE = ("spare", "free")


def tier(c: dict) -> str:
    if c["verdict"] != "wrong":
        return ""
    if c.get("rubric_term") in SPARE_FREE:
        return "wrong_only_primary" if c.get("verdict_alternative") == "correct" else "wrong_both_readings"
    return "no_spare_free_term"


def main(run_id: str, eval_dir: Path | None = None, out_dir: Path | None = None) -> None:
    from .owner_inputs import REVIEW_COLS, REVIEW_KEY, REVIEW_OWNER, UNVER_FILE, WRONG_FILE, merge, review_context
    out = review_out_dir(run_id, eval_dir, out_dir) / "owner_review"   # never the frozen run folder (Log #127)
    eval_dir = long_path(eval_dir or ROOT / "results" / "evaluations" / run_id)        # Log #117
    claims = json.loads((eval_dir / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
    guard_write(out)                                     # frozen run folders are read-only (R59)
    out.mkdir(parents=True, exist_ok=True)
    owner = {}                                           # validate both owner tables before writing anything
    for verdict, table in (("wrong", WRONG_FILE), ("unverifiable", UNVER_FILE)):
        rows = [c for c in claims if c["author"] == "ALLOCATOR" and c["verdict"] == verdict]
        owner[verdict] = merge(rows, eval_dir / "owner_review" / table, REVIEW_COLS[verdict], REVIEW_KEY, REVIEW_OWNER,
                               review_context(rows, verdict))
    for verdict, name in (("wrong", "review_7b_wrong.csv"), ("unverifiable", "review_7c_unverifiable.csv")):
        rows = [c for c in claims if c["author"] == "ALLOCATOR" and c["verdict"] == verdict]
        with open(out / name, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            w.writeheader()
            for c in rows:
                w.writerow({"id": c["id"], "day": c["day"], "field": c["field"], "text": c["text"],
                            "category": c.get("category"), "basis": c.get("basis"), "encoding": encoding(c),
                            "computed": json.dumps(c.get("computed")),
                            "computed_compare": json.dumps(c.get("computed_compare")),
                            "rubric_term": c.get("rubric_term") or "",
                            "verdict_alternative": c.get("verdict_alternative", ""),
                            "computed_alternative": json.dumps(c.get("computed_alternative"))
                            if "computed_alternative" in c else "",
                            "tier": tier(c), "note": c.get("note", ""), **owner[verdict][(c["id"],)]})
        print(name, len(rows))
    wrong = [c for c in claims if c["author"] == "ALLOCATOR" and c["verdict"] == "wrong"]
    tiers = {}
    for c in wrong:
        tiers.setdefault(tier(c), []).append(c["id"])
    summary = {"wrong_claims": len(wrong), "tiers": {k: {"count": len(v), "ids": v} for k, v in sorted(tiers.items())},
               "no_spare_free_term_by_rubric_term": {}}
    for c in wrong:
        if tier(c) == "no_spare_free_term":
            t = c.get("rubric_term") or "arithmetic"
            summary["no_spare_free_term_by_rubric_term"][t] = summary["no_spare_free_term_by_rubric_term"].get(t, 0) + 1
    (out / "wrong_claims_tiers.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v["count"] for k, v in summary["tiers"].items()}),
          summary["no_spare_free_term_by_rubric_term"])


if __name__ == "__main__":
    import argparse
    _a = argparse.ArgumentParser()
    _a.add_argument("run_id")
    _a.add_argument("--out", help="output root (default: results/analysis/recomputed/<run_id>/; Log #127)")
    _a = _a.parse_args()
    main(_a.run_id, out_dir=Path(_a.out) if _a.out else None)
