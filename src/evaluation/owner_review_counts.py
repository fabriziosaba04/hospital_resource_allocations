"""Claim accuracy after the owner review (owner, 2026-11-19, §11 #68). DESCRIPTIVE ONLY: reported next to the
pre-registered recomputation (`explanation_claims.json`), never instead of it. Reads the owner input tables
`owner_review_wrong.csv` and `owner_review_unverifiable.csv`; writes nothing back to them.

    uv run python -m src.evaluation.owner_review_counts R1

Mapping of each pre-registered verdict and owner verdict to a descriptive verdict:
  wrong        confirmed_wrong -> wrong; actually_correct -> correct; extraction_error -> correct (the owner's
               extraction-error verdicts state the claim is correct); should_be_unverifiable -> unverifiable;
               no verdict -> wrong (pending)
  unverifiable confirmed_unverifiable -> unverifiable; verifiable_correct -> correct; verifiable_wrong -> wrong;
               no verdict -> unverifiable (pending); extraction_error -> stops: counted by its recomputed verdict
               under the corrected encoding (§11 #69), which must be supplied first
  correct      unchanged (not reviewed)
The result is provisional while any reviewed list has a row without a verdict. By basis, the encoded `basis` is
used; the owner's comments on R1-D28-05/06 call them copied, and the effect of relabelling them is shown.
Writes `<eval>/owner_review/claim_accuracy_after_owner_review.json`.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from .claim_check import VERDICTS
from .dataset import ROOT
from .owner_inputs import UNVER_FILE, WRONG_FILE
from src.utils.paths import guard_write, long_path

MAP = {"wrong": {"confirmed_wrong": "wrong", "actually_correct": "correct", "extraction_error": "correct",
                 "should_be_unverifiable": "unverifiable", "": "wrong"},
       "unverifiable": {"confirmed_unverifiable": "unverifiable", "verifiable_correct": "correct",
                        "verifiable_wrong": "wrong", "": "unverifiable"}}
OWNER_STATED_COPIED = ("R1-D28-05", "R1-D28-06")      # owner comments: "The claim is correct, copied."


def _count(claims: list[dict], key, basis=lambda c: c.get("basis") or "unclassified") -> dict:
    total = {v: 0 for v in VERDICTS}
    by_cat, by_basis = defaultdict(lambda: {v: 0 for v in VERDICTS}), defaultdict(lambda: {v: 0 for v in VERDICTS})
    for c in claims:
        v = key(c)
        total[v] += 1
        by_cat[c.get("category")][v] += 1
        by_basis[basis(c)][v] += 1
    return {"total": total, "by_category": dict(sorted(by_cat.items())), "by_basis": dict(sorted(by_basis.items()))}


def main(run_id: str, eval_dir: Path | None = None) -> dict:
    ev = long_path(eval_dir or ROOT / "results" / "evaluations" / run_id)        # Log #117
    claims = [c for c in json.loads((ev / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR"]
    own = {}
    for kind, name in (("wrong", WRONG_FILE), ("unverifiable", UNVER_FILE)):
        for r in csv.DictReader(open(ev / "owner_review" / name, encoding="utf-8-sig")):
            own[r["id"]] = (kind, r["owner_verdict"].strip())
    pending = {k: sum(1 for kk, v in own.values() if kk == k and not v) for k in MAP}

    def descriptive(c):
        if c["verdict"] == "correct":
            return "correct"
        kind, v = own[c["id"]]
        assert kind == c["verdict"], c["id"]
        if v not in MAP[kind]:
            raise SystemExit(f"{c['id']}: owner verdict {v!r} on the {kind} list: by §11 #69 it is counted by its "
                             "recomputed verdict under the corrected encoding, which must be supplied first")
        return MAP[kind][v]

    after = _count(claims, descriptive)
    relabel = _count(claims, descriptive, basis=lambda c: "copied" if c["id"] in OWNER_STATED_COPIED
                     else (c.get("basis") or "unclassified"))
    res = {"label": "DESCRIPTIVE, after owner review; reported next to the pre-registered counts, never instead",
           "provisional": any(pending.values()),
           "pending_owner_verdicts": pending,
           "pre_registered": _count(claims, lambda c: c["verdict"]),
           "after_owner_review": after,
           "by_basis_if_D28_05_06_relabelled_copied": relabel["by_basis"],
           "mapping": {k: dict(v) for k, v in MAP.items()}}
    guard_write(ev / "owner_review")                      # frozen run folders are read-only (R59)
    (ev / "owner_review" / "claim_accuracy_after_owner_review.json").write_text(
        json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    return res


if __name__ == "__main__":
    r = main(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("provisional", "pending_owner_verdicts")}, indent=1))
    for k in ("pre_registered", "after_owner_review"):
        print(k, json.dumps(r[k]))
    print("relabel", json.dumps(r["by_basis_if_D28_05_06_relabelled_copied"]))
