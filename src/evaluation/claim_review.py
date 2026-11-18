"""Owner review lists (EVALUATION_PLAN.md §4 item 7b-c): every claim the recomputation marks wrong, and every
claim marked unverifiable, from `<eval>/explanation_claims.json`. No CHECKER matching.

    uv run python -m src.evaluation.claim_review R1
"""

from __future__ import annotations

import csv
import json
import sys

from .dataset import ROOT
from .owner_claims import encoding

COLUMNS = ["id", "day", "field", "text", "category", "basis", "encoding", "computed", "computed_compare",
           "rubric_term", "verdict_alternative", "computed_alternative", "note", "owner_verdict", "owner_comment"]


def main(run_id: str) -> None:
    eval_dir = ROOT / "results" / "evaluations" / run_id
    claims = json.loads((eval_dir / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
    out = eval_dir / "owner_review"
    out.mkdir(exist_ok=True)
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
                            "note": c.get("note", ""), "owner_verdict": "", "owner_comment": ""})
        print(name, len(rows))


if __name__ == "__main__":
    main(sys.argv[1])
