"""Display file for the owner's quick check of the rubric-dependent wrong claims (owner, 2026-11-19). DISPLAY
ONLY: not an input, changes no verdict and no encoding.

    uv run python -m src.evaluation.rubric_check_view R1

Rows: the ALLOCATOR's wrong claims of tier `wrong_only_primary` (bare "spare" / "free", wrong under the strict
reading, correct under the rival one). Columns: the term, the value under each reading, the stated value, the
full sentence of the explanation (a claim quoted with "..." is located by its first part), and every
"above census" / "above occupied" in that sentence with its position relative to the claim's quoted phrase
(inside / before / after). Writes `<eval>/owner_review/rubric_dependent_54_check.csv`.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from .claim_review import tier
from .dataset import ROOT
from .owner_claims import encoding
from src.utils.paths import guard_write, long_path

QUAL = re.compile(r"above (census|occupied)", re.I)
BANNER = ("# GENERATED DISPLAY FILE (src/evaluation/rubric_check_view.py): rubric-dependent wrong claims; "
          "not an input; verdicts go in owner_review_wrong.csv")


def sentence(text: str, quoted: str) -> tuple[str, int, int] | None:
    """The sentence of `text` holding the quoted phrase, and the phrase's span in it."""
    parts = [p.strip() for p in quoted.split("...") if p.strip()]
    for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", text):
        i = s.find(parts[0])
        if i >= 0 and all(p in s[i:] for p in parts):
            j = s.find(parts[-1], i) + len(parts[-1])
            return s, i, j
    return None


def main(run_id: str, eval_dir: Path | None = None, alloc_dir: Path | None = None) -> list[dict]:
    ev = long_path(eval_dir or ROOT / "results" / "evaluations" / run_id)        # Log #117
    alloc = long_path(alloc_dir or ROOT / "results" / "allocations" / run_id)
    claims = json.loads((ev / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
    hist = {}
    for line in open(alloc / "decision_history.jsonl", encoding="utf-8"):
        h = json.loads(line)
        hist[h["day"]] = h["explanation"]                 # last attempt of the day = the accepted one
    rows = []
    for c in claims:
        if c["author"] != "ALLOCATOR" or tier(c) != "wrong_only_primary":
            continue
        day = int(c["id"].split("-D")[1][:2])
        found = sentence(hist[day].get(c["field"], ""), c["text"])
        quals = []
        if found:
            s, i, j = found
            for m in QUAL.finditer(s):
                pos = "inside" if i <= m.start() < j else ("before" if m.start() < i else "after")
                quals.append(f"{m.group(0).lower()} ({pos})")
        rows.append({"id": c["id"], "day": day, "field": c["field"], "text": c["text"],
                     "term": c.get("rubric_term"), "encoding": encoding(c), "strict": json.dumps(c.get("computed")),
                     "rival": json.dumps(c.get("computed_alternative")), "stated": json.dumps(c.get("value")),
                     "qualifiers_in_sentence": "; ".join(quals), "note": c.get("note", ""),
                     "full_sentence": found[0] if found else "(not found)"})
    guard_write(ev / "owner_review")                      # frozen run folders are read-only (R59)
    with open(ev / "owner_review" / "rubric_dependent_54_check.csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(BANNER + "\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    r = main(sys.argv[1])
    print(len(r), "rows;", sum(x["full_sentence"] != "(not found)" for x in r), "sentences found;",
          sum(bool(x["qualifiers_in_sentence"]) for x in r), "with a qualifier in the sentence")
