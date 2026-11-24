"""Step 16: ERROR_ANALYSIS.md, its tables and its number list (Decisions Log #138).

    uv run python src/16_error_analysis.py [--check]

Run after steps 10-14. Writes results/analysis/error_analysis.csv (long format, one id per number; same
convention as steps 10-13), computed only from committed files:

  ea_a1_types      audit issues by type, R1-R3 and STRESS1 (committed deterministic_audit.jsonl)
  ea_a2_claims     R1 claims scored, copied / derived (explanation_claims.json)
  ea_a2_recall     extraction recall both ways, primary (final) and descriptive (comparison_7a_adjudicated.json)
  ea_a2_adjud      discrepancies and their causes (comparison_7a.json, comparison_7a_adjudicated.json)
  ea_a2_accuracy   claim accuracy, pre-registered and after owner review (claim_accuracy_after_owner_review.json)
  ea_a3_missed     audit issues the CHECKER missed, by type (results/analysis/checker_vs_audit.csv, stress1.csv)
  ea_b_*, ea_c     counts over the hand-curated register results/analysis/error_register.csv (parts B, C)
  ea_d             how each error was found: level x detection method

then renders ERROR_ANALYSIS.md from src/evaluation/error_analysis_template.md (the ANALYSIS.md renderer, plus
`{{register:B}}` / `{{register:C}}` for the register's text tables) and writes
results/analysis/ERROR_NUMBERS.csv: every number used, with its source file and script. `--check` writes
nothing and exits 1 if any of the three files is out of date.
"""
import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import (AGENT_RUNS, ANALYSIS_DIR, NUMBER_COLUMNS, Table, audit_days, frac,  # noqa: E402
                                     load_numbers, read_table, render)
from src.utils.paths import guard_write  # noqa: E402

EV = ROOT / "results" / "evaluations" / "R1"
REGISTER = ANALYSIS_DIR / "error_register.csv"
TEMPLATE = ROOT / "src" / "evaluation" / "error_analysis_template.md"
OUT_CSV, OUT_MD, OUT_NUM = ANALYSIS_DIR / "error_analysis.csv", ROOT / "ERROR_ANALYSIS.md", ANALYSIS_DIR / "ERROR_NUMBERS.csv"
SCRIPT = "src/16_error_analysis.py"
PATTERNS = {"silent": "Silent errors (no failing signal when made)", "premise": "False or unchecked premises",
            "scope": "Scope underestimates", "handoff": "Hand-off and state errors",
            "presentation": "Presentation and reporting errors"}
C_KINDS = {"owner_side": "Owner-side discrepancies", "rubric": "Rubric gaps", "extraction": "Extraction errors",
           "specification": "Specification gaps", "consultant_or_owner": "Consultant, owner or record errors caught"}
FOUND_BY = ("test suite", "owner / advisor review", "visual inspection", "agent itself", "independent check",
            "failure in use")   # owner and advisor merged: not separable in the record (R52)
RULES = ("test", "guard", "CLAUDE.md", "procedure", "none")
METHODS = ("deterministic audit or recomputation", "manual review", "matching protocol", "tests and guards",
           "visual inspection", "owner / advisor review", "agent's own check", "independent check or failure in use")
TO_METHOD = {"test suite": METHODS[3], "visual inspection": METHODS[4], "owner / advisor review": METHODS[5],
             "agent itself": METHODS[6], "independent check": METHODS[7],
             "failure in use": METHODS[7]}


ERROR_TYPES = {"queue_count_wrong": "queue count wrong", "quantities_conflated": "two quantities conflated",
               "arithmetic_slip": "arithmetic slip", "sign_error": "sign error",
               "wrong_tier_level": "wrong tier/level", "claim_not_simulated": "claim not simulated",
               "approximation_off": "approximation off"}


def read_table_bom(path: Path) -> list[dict]:
    """An owner input table (written with a BOM); read only."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def register() -> list[dict]:
    rows = read_table(REGISTER)
    for r in rows:
        if r["part"] == "B":
            assert r["pattern"] in PATTERNS, r["id"]
        else:
            assert r["part"] == "C" and r["pattern"] in C_KINDS, r["id"]
        assert r["found_by"] in FOUND_BY and r["rule_added"] in RULES, r["id"]
    return rows


def entries(rid: str) -> int:
    """Number of REFLECTION_LOG entries a register id stands for ('R8, R9, R16' = 3, 'R10-R14' = 5)."""
    m = re.fullmatch(r"R(\d+)-R(\d+)", rid)
    if m:
        return int(m.group(2)) - int(m.group(1)) + 1
    return len(re.findall(r"R\d+", rid)) or 1


def build() -> Table:
    t = Table()
    numbers = load_numbers()
    val = lambda i: numbers[i]["value"]  # noqa: E731

    for run in AGENT_RUNS + ["STRESS1"]:                   # A1: audit issues by type
        c = Counter(i["type"] for d in audit_days(run) for i in d["issues"])
        for ty in ("nurse_gap", "beds_reversal", "nurses_reversal", "reallocation_without_effect"):
            t.add("ea_a1_types", ty, run, c.get(ty, 0), "check", True, "committed deterministic_audit.jsonl")
        t.add("ea_a1_types", "total", run, sum(c.values()), "check", True)
        if run in AGENT_RUNS:                               # the per-run total equals the sum by level
            assert sum(c.values()) == sum(int(val(f"issues_by_level.{lv}.{run}"))
                                          for lv in ("Critical", "Major", "Moderate", "Minor")), run

    claims = [c for c in json.loads((EV / "explanation_claims.json").read_text(encoding="utf-8"))["claims"]
              if c["author"] == "ALLOCATOR"]
    basis = Counter(c.get("basis") for c in claims)
    t.add("ea_a2_claims", "claims scored", "R1", len(claims), "check", True, "explanation_claims.json")
    for b in ("copied", "derived"):
        t.add("ea_a2_claims", f"{b} claims", "R1", basis[b], "check", True, "basis (§4 item 8)")

    adj = json.loads((EV / "owner_extraction" / "comparison_7a_adjudicated.json").read_text(encoding="utf-8"))
    for label, rec, pre in (("primary (final)", adj["primary_recall"]["after_row_57_final"], True),
                            ("descriptive (after adjudication)", adj["descriptive_recall_after_adjudication"]["recall"],
                             False)):
        for side, name in (("a_found_by_b", "owner's claims found by the assistant"),
                           ("b_found_by_a", "assistant's claims found by the owner")):
            for b in ("copied", "derived"):
                t.add("ea_a2_recall", f"{name}, {b}", label, rec[side][b], "check", pre,
                      "days 3, 8, 18 (§4 item 7a); R52 for the descriptive column")
    rows7a = json.loads((EV / "owner_extraction" / "comparison_7a.json").read_text(encoding="utf-8"))["adjudication_rows"]
    causes = adj["causes_total"]
    t.add("ea_a2_adjud", "discrepancies", "count", rows7a["owner_only"] + rows7a["assistant_only"], "descriptive",
          False, f"owner only {rows7a['owner_only']}, assistant only {rows7a['assistant_only']}")
    for k in ("owner_encoding", "owner_miss", "rubric_ambiguity", "matching_rule", "assistant_miss",
              "assistant_encoding"):
        t.add("ea_a2_adjud", k, "count", causes.get(k, 0), "descriptive", False, "R52: causes proposed by an LLM advisor")
    acc = json.loads((EV / "owner_review" / "claim_accuracy_after_owner_review.json").read_text(encoding="utf-8"))
    for col, key, pre in (("pre-registered", "pre_registered", True), ("after owner review", "after_owner_review", False)):
        for v in ("correct", "wrong", "unverifiable"):
            t.add("ea_a2_accuracy", v, col, acc[key]["total"][v], "check", pre,
                  "claim_accuracy_after_owner_review.json" + ("" if pre else "; R52"))

    types = read_table_bom(ANALYSIS_DIR / "R1_owner_error_types.csv")   # the 19 by the owner's typology
    if any(r["owner_confirmed"].strip() != "yes" for r in types):
        raise SystemExit("R1_owner_error_types.csv: not every row is confirmed by the owner")
    for et, name in ERROR_TYPES.items():
        ids = [r["claim_id"] for r in types if r["error_type"].strip() == et]
        t.add("ea_a2_types", name, "claims", len(ids), "descriptive", False, "R52; R1_owner_error_types.csv")
        t.add("ea_a2_types", name, "claim ids", " ".join(i.replace("R1-", "") for i in ids), "descriptive", False)

    missed = Counter()                                      # A3: audit issues the CHECKER missed, by type
    for run in AGENT_RUNS + ["STRESS1"]:
        for ty in ("nurse_gap", "beds_reversal", "nurses_reversal", "reallocation_without_effect"):
            m, a = map(int, val(f"checker_{run}.type_{ty}.recall").split("/"))
            t.add("ea_a3_missed", ty, run, a - m, "check", run != "STRESS1",
                  "audit issues of this type not matched (§4 items 4-5)")
            missed[run] += a - m
        t.add("ea_a3_missed", "total missed", run, missed[run], "check", run != "STRESS1")

    reg = register()                                        # B and C counts
    b = [r for r in reg if r["part"] == "B"]
    c = [r for r in reg if r["part"] == "C"]
    t.add("ea_b_total", "cases", "rows", len(b), "descriptive", False, "rows of error_register.csv, part B")
    t.add("ea_b_total", "cases", "REFLECTION_LOG entries", sum(entries(r["id"]) for r in b), "descriptive", False)
    t.add("ea_b_total", "cases", "with a rule added", sum(1 for r in b if r["rule_added"] != "none"),
          "descriptive", False, "test, guard, CLAUDE.md rule or documented procedure")
    for p, name in PATTERNS.items():
        mine = [r for r in b if r["pattern"] == p]
        t.add("ea_b_patterns", name, "cases", len(mine), "descriptive", False, " ".join(r["id"] for r in mine))
        t.add("ea_b_patterns", name, "with a rule added", sum(1 for r in mine if r["rule_added"] != "none"),
              "descriptive", False)
    for f in FOUND_BY:
        t.add("ea_b_found_by", f, "cases", sum(1 for r in b if r["found_by"] == f), "descriptive", False)
    for rl in RULES:
        t.add("ea_b_rules", rl, "cases", sum(1 for r in b if r["rule_added"] == rl), "descriptive", False)
    for k, name in C_KINDS.items():
        t.add("ea_c", name, "register rows", sum(1 for r in c if r["pattern"] == k), "descriptive", False)

    # D: how each error was found (level x method); every cell names its unit
    def d_row(level, unit, cells):
        t.add("ea_d", level, "unit", unit, "descriptive", False)
        for mth in METHODS:
            t.add("ea_d", level, mth, cells.get(mth, 0), "descriptive", False)
    d_row("allocation decisions, R1-R3", "audit issues",
          {METHODS[0]: sum(int(val(f"issues_by_level.{lv}.{r}")) for r in AGENT_RUNS
                           for lv in ("Critical", "Major", "Moderate", "Minor"))})
    d_row("allocation decisions, STRESS1", "audit issues",
          {METHODS[0]: sum(len(d["issues"]) for d in audit_days("STRESS1"))})
    d_row("explanation claims, R1", "wrong claims",
          {METHODS[0]: int(val("wrong_claims_sets.pre_registered_wrong_claims.size")),
           METHODS[1]: int(val("wrong_claims_sets.confirmed_wrong_after_owner_review.size"))})
    pooled = [tuple(map(int, val(f"checker_{r}.pooled_reference_only.recall").split("/"))) for r in AGENT_RUNS]
    rep = [tuple(map(int, val(f"checker_{r}.pooled_reference_only.precision").split("/"))) for r in AGENT_RUNS]
    d_row("CHECKER: audit issues missed, R1-R3", "audit issues", {METHODS[2]: sum(a - m for m, a in pooled)})
    d_row("CHECKER: reports without an audit match, R1-R3", "CHECKER issues", {METHODS[2]: sum(n - m for m, n in rep)})
    w_m, w_n = map(int, val("wrong_claims_primary.all_wrong_claims.recall").split("/"))
    d_row("CHECKER: wrong claims not contested, R1", "wrong claims", {METHODS[2]: w_n - w_m})
    d_row("CHECKER: wrong disputes, R1", "contested correct claims",
          {METHODS[5]: int(val("wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes"))})
    dev = Counter(TO_METHOD[r["found_by"]] for r in b)
    d_row("development (coding agent)", "cases", dict(dev))
    d_row("verification: owner-side discrepancies", "claims", {METHODS[1]: rows7a["owner_only"] + rows7a["assistant_only"]})
    d_row("verification: rubric-dependent readings", "claims",
          {METHODS[6]: int(val("wrong_claims_sets.rubric_dependent_spare_free.size"))})
    d_row("verification: extraction errors", "claims", {METHODS[1]: int(val("wrong_claims_sets.extraction_error.size"))})
    d_row("verification: specification gaps", "REFLECTION_LOG entries",
          {METHODS[6]: sum(entries(r["id"]) for r in c if r["pattern"] == "specification")})
    cons = Counter(TO_METHOD[r["found_by"]] for r in c if r["pattern"] == "consultant_or_owner")
    d_row("verification: consultant, owner or record errors", "cases", dict(cons))
    return t


def register_table(part: str) -> str:
    reg = [r for r in register() if r["part"] == part]
    groups = PATTERNS if part == "B" else C_KINDS
    cell = lambda s: s.replace("|", "\\|")  # noqa: E731
    out = []
    for key, name in groups.items():
        mine = [r for r in reg if r["pattern"] == key]
        if not mine:
            continue
        out += [f"**{name}**", "",
                "| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        out += [f"| {r['id']} | {cell(r['what'])} | {cell(r['where'])} | {cell(r['how_found'])} | {r['found_by']} | "
                f"{cell(r['consequence'])} | {cell(r['fix'])} | {r['rule_added']} |" for r in mine]
        out.append("")
    out.append(f"*Source: [`results/analysis/error_register.csv`](results/analysis/error_register.csv) (hand-curated "
               f"from `docs/REFLECTION_LOG.md`, the id of each row), rendered by `{SCRIPT}`.*")
    return "\n".join(out)


def expected(table_csv: str) -> tuple[str, str]:
    numbers = load_numbers()
    for r in csv.DictReader(io.StringIO(table_csv)):
        numbers[r["id"]] = {**r, "source_file": "results/analysis/error_analysis.csv", "script": SCRIPT}
    tpl = TEMPLATE.read_text(encoding="utf-8")
    tpl = tpl.replace("{{register:B}}", register_table("B")).replace("{{register:C}}", register_table("C"))
    text, used = render(tpl, numbers, "results/analysis/ERROR_NUMBERS.csv")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=NUMBER_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(used)
    return text, buf.getvalue()


def table_csv(t: Table) -> str:
    from src.evaluation.analysis import COLUMNS
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(t.rows)
    return buf.getvalue()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    tab = table_csv(build())
    text, nums = expected(tab)
    files = ((OUT_CSV, tab), (OUT_MD, text), (OUT_NUM, nums))
    if a.check:
        bad = [p.name for p, s in files if not p.exists() or p.read_text(encoding="utf-8") != s]
        print("up to date" if not bad else f"OUT OF DATE: {bad}")
        sys.exit(1 if bad else 0)
    for p, s in files:
        guard_write(p).write_text(s, encoding="utf-8", newline="\n")
    print(f"wrote {OUT_CSV.name}, ERROR_ANALYSIS.md, {OUT_NUM.name} ({nums.count(chr(10)) - 1} numbers)")
