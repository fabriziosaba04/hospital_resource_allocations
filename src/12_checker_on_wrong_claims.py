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
from src.evaluation.owner_inputs import OwnerInputError, read_table  # noqa: E402
from src.evaluation.owner_review_counts import MAP  # noqa: E402
from src.utils.paths import guard_write  # noqa: E402

EV = ROOT / "results" / "evaluations" / "R1"
MAPPING = ANALYSIS_DIR / "R1_checker_dispute_mapping.json"
R52 = "R52: the 19 rest on verdicts proposed by an LLM advisor and accepted by the owner"


def owner_verdicts() -> dict[str, tuple[str, str]]:
    out = {}
    for kind, name in (("wrong", "owner_review_wrong.csv"), ("unverifiable", "owner_review_unverifiable.csv")):
        for r in csv.DictReader(open(EV / "owner_review" / name, encoding="utf-8-sig")):
            out[r["id"]] = (kind, r["owner_verdict"].strip())
    return out


ERROR_FILE = ANALYSIS_DIR / "R1_owner_error_types.csv"     # owner input table: read, never written
ERROR_COLS = ["claim_id", "day", "text", "error_type", "basis", "set_by", "owner_confirmed"]
ERROR_TYPES = {"queue_count_wrong": "queue count wrong", "quantities_conflated": "two quantities conflated",
               "arithmetic_slip": "arithmetic slip", "sign_error": "sign error",
               "wrong_tier_level": "wrong tier/level", "claim_not_simulated": "claim not simulated",
               "approximation_off": "approximation off"}
R52_TYPES = "R52: typology proposed by a consultant (LLM advisor) and confirmed by the owner"


def error_types(claims: list[dict], confirmed: set[str]) -> tuple[dict[str, str], int]:
    """The owner's error type per confirmed wrong claim, validated as the other owner input tables are
    (`owner_inputs.read_table`): exact header, the 19 ids, context columns equal to the claims, allowed values.
    Returns the types and the number of rows with owner_confirmed = yes."""
    tab = read_table(ERROR_FILE, ERROR_COLS, ("claim_id",))
    ids = {k[0] for k in tab}
    if ids != confirmed:
        raise OwnerInputError(f"{ERROR_FILE.name}: ids missing {sorted(confirmed - ids)}, extra {sorted(ids - confirmed)}")
    by_id = {c["id"]: c for c in claims}
    for (i,), r in tab.items():
        line = r["__line__"]
        if (r["day"].strip(), r["text"].strip()) != (str(by_id[i]["day"]), by_id[i]["text"].strip()):
            raise OwnerInputError(f"{ERROR_FILE.name}: {i} (line {line}) day/text differ from the claim")
        for col, allowed in (("error_type", ERROR_TYPES), ("set_by", ("assistant_prefill", "owner")),
                             ("owner_confirmed", ("", "yes"))):
            if r[col].strip() not in allowed:
                raise OwnerInputError(f"{ERROR_FILE.name}: {i} (line {line}) column {col!r} is {r[col]!r}")
    return ({i: r["error_type"].strip() for (i,), r in tab.items()},
            sum(1 for r in tab.values() if r["owner_confirmed"].strip() == "yes"))


def write_mapping_md(mp: dict, claims: list[dict], own: dict, types: dict[str, str], out_dir: Path) -> Path:
    """A readable copy of the mapping for the owner's review (generated; the JSON is the input)."""
    by_id = {c["id"]: c for c in claims}
    reps = [json.loads(x) for x in (EV / "validation_history.jsonl").read_text(encoding="utf-8").splitlines() if x]
    issue = {(r["day"], i["day"], i["type"]): i for r in reps for i in r["report"]["issues"]}
    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = ["# R1: the CHECKER's explanation findings and the claims they contest", "",
             "*Generated by `src/12_checker_on_wrong_claims.py` from "
             "[`R1_checker_dispute_mapping.json`](R1_checker_dispute_mapping.json) (the input; edit that file, "
             "not this one). **Assistant-mapped, owner-reviewed (R52).***", "",
             f"Owner review: {mp['owner_review']}", "",
             f"Rule: {mp['rule']}", "",
             f"Findings: {len(mp['findings'])} (every CHECKER issue of an LLM-only type on R1). The CHECKER's other "
             "issues on R1 are of the audit's types (allocations, not explanations); a keyword search of their text "
             "found none that disputes an explanation figure.", ""]
    for n, f in enumerate(mp["findings"], 1):
        i = issue[(f["report_day"], f["issue_day"], f["type"])]
        lines += [f"## Finding {n}: day {f['issue_day']}, {f['type']} ({f['severity']}), report of day "
                  f"{f['report_day']}", "",
                  f"- **What happened (CHECKER):** {i.get('what_happened', '')}",
                  f"- **What should have happened (CHECKER):** {i.get('what_should_have_happened', '')}",
                  f"- **Why incorrect (CHECKER):** {i.get('why_incorrect', '')}",
                  f"- **Mapping reason:** {f['reason']}",
                  f"- **Owner review:** {f['owner_review']}",
                  f"- **CHECKER's own figure equals the recomputed value:** "
                  f"{ {True: 'yes', False: 'no', None: 'not applicable'}[f['checker_value_equals_recomputed']] }", ""]
        rows = [(cid, "contested") for cid in f["contests"]] + [(cid, "not contested") for cid in f["not_contested"]]
        if not rows:
            lines += ["No claim is contested.", ""]
            continue
        lines += ["| Claim | Mapped | Field | Claim text | Stated | Recomputed | Verdict (pre-registered) | "
                  "Owner verdict | Error type |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for cid, how in rows:
            c = by_id[cid]
            lines.append(f"| {cid} | {how} | {c['field']} | {cell(c['text'])} | {cell(c['value'])} | "
                         f"{cell(c['computed'])} | {c['verdict']} | {own.get(cid, ('', '–'))[1] or '–'} | "
                         f"{ERROR_TYPES.get(types.get(cid, ''), '–')} |")
        lines.append("")
    path = guard_write(Path(out_dir) / "R1_checker_dispute_mapping.md")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


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
    if "owner_review" not in mp or any(not f.get("owner_review") for f in mp["findings"]):
        raise SystemExit("mapping: every finding needs its owner_review (Decisions Log #134)")
    return mp


def build(out_dir: Path = ANALYSIS_DIR) -> Table:
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
    # the owner's review of the mapping (Log #134) must agree with the descriptive scoring
    founded = {i for f in mp["findings"] if f["owner_review"].startswith("well-founded") for i in f["contests"]}
    wrongd = {i for f in mp["findings"] if f["owner_review"].startswith("wrong dispute") for i in f["contests"]}
    if founded != set(disputed) & strata["confirmed wrong"] or wrongd != set(desc["wrong_disputes"]):
        raise SystemExit("mapping: the owner review disagrees with the descriptive scoring")
    t.add(tab, "confirmed wrong claims", "disputes the owner judged well-founded", len(founded), "descriptive",
          False, " ".join(sorted(founded)) + "; owner review of the mapping (Log #134)")

    confirmed = strata["confirmed wrong"]                   # the 19 by error type (§11 #73; owner, 2026-11-24)
    types, n_ok = error_types(claims, confirmed)
    tab = "wrong_claims_by_error_type"
    if n_ok == len(confirmed):
        for et in ERROR_TYPES:
            ids = {i for i, v in types.items() if v == et}
            hit = sorted(ids & set(disputed))
            t.add(tab, ERROR_TYPES[et], "recall", frac(len(hit), len(ids)), "descriptive", False,
                  (" ".join(hit) or "none") + "; " + R52_TYPES)
        queue ={c["id"]: c for c in claims if types.get(c["id"]) == "queue_count_wrong"}
        sub = {"L2/L1 off-by-one": [], "L2/L1 swap (off by 2)": [], "queue total off by one": []}
        for i, c in sorted(queue.items()):
            diff = abs(float(c["value"]) - float(c["computed"]))
            lv = c["quantity"].get("levels")
            key = ("L2/L1 off-by-one" if lv and diff == 1 else "L2/L1 swap (off by 2)" if lv and diff == 2
                   else "queue total off by one" if not lv and diff == 1 else None)
            if key is None:
                raise SystemExit(f"{i}: queue error outside the three described forms")
            sub[key].append(i)
        for key, ids in sub.items():
            t.add("queue_errors", key, "claims", frac(len(ids), len(queue)), "descriptive", False,
                  " ".join(ids) + "; recomputed |stated - computed| and the levels named")
    else:
        t.add(tab, "stratification by error type", "status", f"pending: {n_ok}/{len(confirmed)} rows confirmed",
              "descriptive", False, f"{ERROR_FILE.name}: owner_confirmed must be 'yes' on every row before use")
    tab = "wrong_claims_by_category"                       # secondary breakdown: category is a topic
    for cat in sorted({c["category"] for c in claims if c["id"] in confirmed}):
        ids = {c["id"] for c in claims if c["id"] in confirmed and c["category"] == cat}
        hit = sorted(ids & set(disputed))
        t.add(tab, cat, "recall", frac(len(hit), len(ids)), "descriptive", False,
              (" ".join(hit) or "none") + "; secondary breakdown: category is a topic, not an error type")

    tab = "checker_explanation_findings"                    # what the precision rests on (owner, 2026-11-24)
    mapped = [f for f in mp["findings"] if f["contests"]]
    unmapped = [f for f in mp["findings"] if not f["contests"]]
    t.add(tab, "explanation findings", "mapped", len(mapped), "descriptive", False, "contest at least one claim")
    t.add(tab, "explanation findings", "unmapped", len(unmapped), "descriptive", False,
          "; ".join(f"day {f['issue_day']} {f['type']}: {f['reason']}" for f in unmapped) or "none")
    t.add(tab, "explanation findings", "total", len(mp["findings"]), "descriptive", False,
          "all CHECKER issues of the LLM-only types on R1; none of its other issues disputes an explanation figure")
    wrong_c = {c["id"] for c in claims if c["verdict"] == "wrong"}
    t.add(tab, "findings contesting a pre-registered wrong claim", "value",
          frac(sum(1 for f in mapped if set(f["contests"]) & wrong_c), len(mp["findings"])), "descriptive", False,
          "over all explanation findings, unmapped included")
    t.add(tab, "findings contesting a confirmed wrong claim", "value",
          frac(sum(1 for f in mapped if set(f["contests"]) & confirmed), len(mp["findings"])), "descriptive", False,
          "over all explanation findings, unmapped included; " + R52)
    write_mapping_md(mp, claims, own, types if n_ok == len(confirmed) else {}, out_dir)

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
    out_dir = Path(ap.parse_args().out)
    out = Table.write(build(out_dir), out_dir / "checker_on_wrong_claims.csv")
    print(f"wrote {out}")
