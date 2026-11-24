"""Step 12: the CHECKER on R1's wrong explanation claims (EVALUATION_PLAN.md §4, explanation claims item 4;
PROJECT_SPEC.md §11 #73; Decisions Log #130).

    uv run python src/12_checker_on_wrong_claims.py [--out DIR]      # default: results/analysis/

Inputs (read only): the committed scored claims results/evaluations/R1/explanation_claims.json (re-verified
EQUAL by src/08), the owner's verdicts owner_review/owner_review_wrong.csv and owner_review_unverifiable.csv
(applied with `owner_review_counts.MAP`), and the CHECKER mapping results/analysis/R1_checker_dispute_mapping.json.
Scoring is `claim_check.checker_on_claims`. Writes `<out>/checker_on_wrong_claims.csv`:

  wrong_claims_primary      against the 75 pre-registered wrong claims (primary): recall, precision, wrong
                            disputes; and recall per stratum, 75 = 54 rubric-dependent + 2 extraction errors +
                            19 confirmed (§11 #73)
  wrong_claims_descriptive  against the 19 confirmed_wrong after owner review (descriptive; verdicts proposed by
                            an LLM advisor and accepted by the owner, REFLECTION_LOG R52)
  wrong_claims_cases        the two cases the owner asked about (spare/free readings; day-12 self-verification)
All figures matched/total, no standalone percentages (§11 #73).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import ANALYSIS_DIR, Table, frac  # noqa: E402
from src.evaluation.claim_check import checker_on_claims  # noqa: E402
from src.evaluation.owner_review_counts import MAP  # noqa: E402

EV = ROOT / "results" / "evaluations" / "R1"
MAPPING = ANALYSIS_DIR / "R1_checker_dispute_mapping.json"
R52 = "R52: the 19 rest on verdicts proposed by an LLM advisor and accepted by the owner"


def owner_verdicts() -> dict[str, tuple[str, str]]:
    out = {}
    for kind, name in (("wrong", "owner_review_wrong.csv"), ("unverifiable", "owner_review_unverifiable.csv")):
        for r in csv.DictReader(open(EV / "owner_review" / name, encoding="utf-8-sig")):
            out[r["id"]] = (kind, r["owner_verdict"].strip())
    return out


def checked_mapping(claims: list[dict]) -> dict:
    mp = json.loads(MAPPING.read_text(encoding="utf-8"))
    ids = {c["id"] for c in claims}
    listed = sorted(i for f in mp["findings"] for i in f["contests"])
    if listed != sorted(mp["disputed_by_checker"]) or not set(listed) <= ids:
        raise SystemExit("mapping: findings and disputed_by_checker disagree, or an id is not an R1 claim")
    reps = [json.loads(x) for x in (EV / "validation_history.jsonl").read_text(encoding="utf-8").splitlines() if x]
    llm = sorted((r["day"], i["day"], i["type"]) for r in reps for i in r["report"]["issues"]
                 if i.get("type") in ("explanation_inaccuracy", "information_leak", "inconsistency", "other"))
    if llm != sorted((f["report_day"], f["issue_day"], f["type"]) for f in mp["findings"]):
        raise SystemExit(f"mapping: the findings listed are not the CHECKER's LLM-only issues {llm}")
    return mp


def build() -> Table:
    claims = [c for c in json.loads((EV / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR"]
    mp = checked_mapping(claims)
    disputed = mp["disputed_by_checker"]
    own = owner_verdicts()
    tiers = json.loads((EV / "owner_review" / "wrong_claims_tiers.json").read_text(encoding="utf-8"))["tiers"]
    wrong = {c["id"] for c in claims if c["verdict"] == "wrong"}
    strata = {"rubric-dependent (spare/free)": set(tiers["wrong_only_primary"]["ids"]),
              "extraction error": {i for i in wrong if own[i] == ("wrong", "extraction_error")},
              "confirmed wrong": {i for i in wrong if own[i] == ("wrong", "confirmed_wrong")}}
    if strata["rubric-dependent (spare/free)"] != {i for i in wrong if own[i] == ("wrong", "actually_correct")} \
            or sum(map(len, strata.values())) != len(wrong) or set().union(*strata.values()) != wrong:
        raise SystemExit(f"the strata do not partition the {len(wrong)} wrong claims as §11 #73 states")
    t = Table()

    tab = "wrong_claims_sets"                              # sizes of the reference sets (§11 #73)
    t.add(tab, "pre-registered wrong claims", "size", len(wrong), "check", True)
    for name, ids in strata.items():
        t.add(tab, name, "size", len(ids), "check", True)
    t.add(tab, "CHECKER LLM-only issues on R1", "size", len(mp["findings"]), "descriptive", True,
          "the findings the mapping covers")

    pre = checker_on_claims(claims, disputed)              # primary: pre-registered verdicts
    tab = "wrong_claims_primary"
    t.add(tab, "all wrong claims", "recall", pre["recall"], "check", True, "pre-registered verdicts (§4 item 4)")
    t.add(tab, "all wrong claims", "precision", pre["precision"], "check", True)
    t.add(tab, "all wrong claims", "wrong disputes", len(pre["wrong_disputes"]), "check", True,
          " ".join(pre["wrong_disputes"]) or "none")
    t.add(tab, "all wrong claims", "contested unverifiable", len(pre["contested_unverifiable"]), "check", True)
    t.add(tab, "all wrong claims", "disputes outside the universe", len(pre["disputes_outside_universe"]),
          "check", True)
    for name, ids in strata.items():
        hit = sorted(ids & set(disputed))
        t.add(tab, name, "recall", frac(len(hit), len(ids)), "check", True, " ".join(hit) or "none")

    def after(c):                                           # descriptive: verdicts after owner review
        return c["verdict"] if c["verdict"] == "correct" else MAP[own[c["id"]][0]][own[c["id"]][1]]
    desc = checker_on_claims([{**c, "verdict": after(c)} for c in claims], disputed)
    if desc["wrong_claims"] != len(strata["confirmed wrong"]):
        raise SystemExit("descriptive reference set is not the confirmed_wrong claims")
    tab = "wrong_claims_descriptive"
    t.add("wrong_claims_sets", "confirmed wrong after owner review", "size", desc["wrong_claims"], "descriptive",
          True, R52)
    t.add(tab, "confirmed wrong claims", "recall", desc["recall"], "descriptive", True, R52)
    t.add(tab, "confirmed wrong claims", "precision", desc["precision"], "descriptive", True, R52)
    t.add(tab, "confirmed wrong claims", "wrong disputes", len(desc["wrong_disputes"]), "descriptive", True,
          " ".join(desc["wrong_disputes"]) + " (owner verdict actually_correct)")
    # The stratification of the 19 "by error type" (§11 #73) is pending the owner's choice of what "error
    # type" means (open question, 2026-11-24); no stratified row is written until then.

    tab = "wrong_claims_cases"
    rubric = strata["rubric-dependent (spare/free)"]
    f28 = next(f for f in mp["findings"] if f["issue_day"] == 28)
    t.add(tab, "spare/free: rubric-dependent claims contested", "value",
          frac(len(rubric & set(disputed)), len(rubric)), "descriptive", False, " ".join(sorted(rubric & set(disputed))))
    t.add(tab, "spare/free: CHECKER findings that contest a claim on the strict reading", "value", 0,
          "descriptive", False, "the one finding on such claims (day 28) uses beds minus census itself, "
          "computed on the day-27 allocation: " + f28["reason"].split("The CHECKER's figures are ")[1])
    t.add(tab, "day 12: queue total R1-D12-19 contested", "value", "yes" if "R1-D12-19" in disputed else "no",
          "descriptive", False, "the figure 16 (recomputed 17)")
    t.add(tab, "day 12: 'matches the queue records' visible to the CHECKER", "value", "no", "descriptive", False,
          "the sentence is in the ALLOCATOR's closing message (transcript; allocator_digest/day_12.md), not in "
          "the submitted explanation; no CHECKER tool returns transcripts (CHECKER tools: Decisions Log #73)")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ANALYSIS_DIR))
    out = Table.write(build(), Path(ap.parse_args().out) / "checker_on_wrong_claims.csv")
    print(f"wrote {out}")
