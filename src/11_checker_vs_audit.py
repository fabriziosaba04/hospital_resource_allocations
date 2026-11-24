"""Step 11: the CHECKER against the deterministic audit, R1-R3, run by run (EVALUATION_PLAN.md §4 "Use in
evaluation" items 4-8; Decisions Log #128-#129).

    uv run python src/11_checker_vs_audit.py [--out DIR]      # default: results/analysis/

Matching is `checker_matching.match` on (day, type), with the audit issues of the periods the CHECKER reported
on (as `run_report.build`), read from the committed deterministic_audit.jsonl and validation_history.jsonl. The
result must equal the committed run_report.json `checker_overall` (rebuilt EQUAL by src/07). Writes
`<out>/checker_vs_audit.csv`:

  checker_<run>    recall, precision and level agreement as matched/total (§4 item 6), by group (§11 #43;
                   rejected_submission its own row), by level, by type (all 11 agent-attributable types);
                   the pooled figure is kept for reference only (§4 item 5)
  checker_extra    date-shift matches (descriptive, §4 item 7), the CHECKER's LLM-only issues (reported apart,
                   LLM-dependent), unmatchable CHECKER issues, and the independent recount check
No figure is pooled across runs: §4 defines none (item 6 applies "to every stratum and to R1-R3").

Pipeline check (stop rule of the Phase 2 brief): matched per (day, type) is recounted here as
min(audit, CHECKER) directly from the two record files, without `checker_matching`; any difference exits 2.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import AGENT_RUNS, ANALYSIS_DIR, Table, audit_days, frac  # noqa: E402
from src.evaluation.checker_matching import (AGENT_TYPES, HEADLINE, HEADLINE_SEPARATE, LEVELS,  # noqa: E402
                                             SECONDARY, match)

GROUPS = (("headline", "headline group"), ("headline_rejected_submission", "rejected_submission (own row)"),
          ("secondary", "secondary group"))
REVERSAL_NOTE = "reversal recall measures reading of tau, not discovery (§4 item 8)"


def reports(run: str) -> list[dict]:
    p = ROOT / "results" / "evaluations" / run / "validation_history.jsonl"
    return [r for r in (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
            if r.get("kind") == "report"]


def inputs(run: str, days: set[int] | None = None) -> tuple[list[dict], list[dict]]:
    """Audit issues inside the reported periods and the CHECKER issues, optionally restricted to `days`."""
    reps = reports(run)
    periods = [(r["report"]["period"]["from_day"], r["report"]["period"]["to_day"]) for r in reps]
    audit = [i for d in audit_days(run) for i in d["issues"] if any(lo <= i["day"] <= hi for lo, hi in periods)]
    checker = [i for r in reps for i in r["report"]["issues"]]
    if days is not None:
        audit = [i for i in audit if int(i["day"]) in days]
        checker = [i for i in checker if str(i.get("day")).lstrip("-").isdigit() and int(i["day"]) in days]
    return audit, checker


def recount(audit: list[dict], checker: list[dict]) -> Counter:
    """Independent of checker_matching: matched per type = sum over days of min(audit, CHECKER)."""
    a = Counter((int(i["day"]), i["type"]) for i in audit if i["type"] in AGENT_TYPES)
    c = Counter((int(i["day"]), i["type"]) for i in checker if i.get("type") in AGENT_TYPES)
    out = Counter()
    for k in set(a) | set(c):
        out[k[1]] += min(a[k], c[k])
    return out


def stratum(t: Table, table: str, row: str, s: dict, note: str = "", pre: bool = True, role: str = "check") -> None:
    t.add(table, row, "recall", frac(s["matched"], s["audit"]), role, pre, note)
    t.add(table, row, "precision", frac(s["checker_matched"], s["checker"]), role, pre, note)
    t.add(table, row, "level agreement", frac(s["level_same"], s["matched"]), role, pre, note)


def add_matching(t: Table, table: str, m: dict, pre: bool = True, role: str = "check") -> None:
    for key, label in GROUPS:
        stratum(t, table, label, m["by_group"][key], pre=pre, role=role,
                note=REVERSAL_NOTE if key == "secondary" else ("not folded into the headline group (§11 #43)"
                                                               if key == "headline_rejected_submission" else ""))
    for lv in LEVELS:
        stratum(t, table, f"level {lv}", m["by_level"][lv], pre=pre, role=role)
    for ty in AGENT_TYPES:
        stratum(t, table, f"type {ty}", m["by_type"][ty], pre=pre, role=role,
                note=REVERSAL_NOTE if ty.endswith("reversal") else "")
    pooled = {"matched": m["matched"], "audit": m["audit_issues"], "checker": m["checker_issues"],
              "checker_matched": m["matched"], "level_same": m["level_same"]}
    stratum(t, table, "pooled (reference only)", pooled, pre=pre, role=role,
            note="kept for reference, not a headline (§4 item 5)")


def check_recount(run: str, audit: list[dict], checker: list[dict], m: dict) -> None:
    rc = recount(audit, checker)
    mine = {ty: m["by_type"][ty]["matched"] for ty in AGENT_TYPES}
    if any(rc[ty] != mine[ty] for ty in AGENT_TYPES):
        print(f"STOP: {run}: independent recount {dict(rc)} differs from checker_matching {mine}")
        sys.exit(2)


def build() -> Table:
    t = Table()
    for run in AGENT_RUNS:
        audit, checker = inputs(run)
        m = match(audit, checker, counts=True)
        committed = json.loads((ROOT / "results" / "evaluations" / run / "run_report.json")
                               .read_text(encoding="utf-8"))["checker_overall"]
        for k in ("audit_issues", "checker_issues", "matched", "recall", "precision", "level_agreement"):
            if committed[k] != m[k]:
                print(f"STOP: {run}: {k} = {m[k]} here, {committed[k]} in the committed run report")
                sys.exit(2)
        check_recount(run, audit, checker, m)
        add_matching(t, f"checker_{run}", m)
        t.add("checker_extra", "date-shift matches (1-2 days)", run, len(m["date_shift_matches"]), "descriptive",
              True, "among issues the primary rule leaves unmatched; never instead of it (§4 item 7)")
        for ty in ("explanation_inaccuracy", "information_leak", "inconsistency", "other"):
            t.add("checker_extra", f"CHECKER LLM-only issues: {ty}", run, m["checker_llm_only"].get(ty, 0),
                  "descriptive", True, "LLM-dependent, reported apart (§4 item 4)")
        t.add("checker_extra", "CHECKER issues with an unmatchable type or day", run, m["checker_unmatchable"],
              "descriptive", True)
        t.add("checker_extra", "independent recount of matched per (day, type)", run, "equal", "check", False,
              "min(audit, CHECKER) per key, recounted without checker_matching")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ANALYSIS_DIR))
    out = Table.write(build(), Path(ap.parse_args().out) / "checker_vs_audit.csv")
    print(f"wrote {out}")
