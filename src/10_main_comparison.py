"""Step 10: main comparison, R1-R3 against B0-B2 on the primary dataset (EVALUATION_PLAN.md §3, §4 item 2,
§8, §9; Decisions Log #128).

    uv run python src/10_main_comparison.py [--out DIR]      # default: results/analysis/

Recomputes the audit and metrics of R1-R3 and B0-B2 on `seed20261107` from the committed records
(`metrics.evaluate_run`; the baselines must equal their committed metrics.json) and writes
`<out>/main_comparison.csv` (long format, `src/evaluation/analysis.py`):

  gate_d           gate D and its components, and the reported counts (§3.7), per run
  issues_by_level  audit issue counts by level, per policy (§4 "Use in evaluation" item 2: compared
                   lexicographically, no weighted sum)
  main_headline / main_secondary / main_descriptive
                   every §3 metric, run by run, next to B0, B1, B2 and the floor (§3.10 roles)
  main_gap         headline metrics read as the gap to B1 and to the floor, run by run (§1, §3.10)
  main_lex         A2 read lexicographically (tier 3, then 2, then 1) against B1, per run (§3.2)
  main_variability per metric: min, max and mean over R1-R3 (§9: "the value for each run (R1-R3), with the
                   range (min-max) and the mean"). The mean is reported only because §9 defines it.

Stops (exit 2) if the floor of a metric differs between policies (it is policy-independent) or if a run equals
B1 on every metric (stop rule of the Phase 2 brief: check the pipeline before reporting such a result).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import (AGENT_RUNS, ANALYSIS_DIR, BASELINES, PRIMARY, Table, audit_days, frac,  # noqa: E402
                                     lexicographic, metric_rows, policy_metrics)

TABLE = {"headline": "main_headline", "secondary": "main_secondary", "context": "main_secondary",
         "descriptive": "main_descriptive"}


def halts(run: str) -> int:
    wf = ROOT / "results" / "allocations" / run / "workflow.jsonl"
    return sum(1 for x in wf.read_text(encoding="utf-8").splitlines() if x.strip() and json.loads(x)["event"] == "halted")


def final_allocations(run: str) -> dict[int, dict]:
    """The allocation in effect at the end of each day: the last Allocation State record of the day that is not
    the initial rule (as run_report.build)."""
    p = ROOT / "results" / "allocations" / run / "allocation_state.jsonl"
    out = {}
    for x in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()):
        if x["source"] != "initial_rule":
            out[x["day"]] = {"beds": x["beds"], "nurses": x["nurses"]}
    return out


def build() -> Table:
    pol = {r: policy_metrics(r) for r in AGENT_RUNS}
    pol.update({b: policy_metrics(f"{b}-{PRIMARY}", PRIMARY) for b in BASELINES})
    rows = {p: metric_rows(m) for p, m in pol.items()}
    t = Table()

    for r in AGENT_RUNS:                                   # gate D (§3.7)
        d = pol[r]["D"]
        for key, label, role in (("gate_passed", "gate passed", "gate"),
                                 ("hard_constraint_violations_in_effect", "hard-constraint violations in effect", "gate"),
                                 ("replay_mismatches", "replay mismatches", "gate"),
                                 ("pairing_closed_form_mismatches", "pairing / closed-form mismatches", "gate"),
                                 ("rejected_submissions", "rejected submissions", "gate"),
                                 ("failure_days", "ALLOCATOR failure days", "gate")):
            t.add("gate_d", label, r, d[key], role, True)
        t.add("gate_d", "halts", r, halts(r), "gate", True, "workflow.jsonl events 'halted'")

    for lv in ("Critical", "Major", "Moderate", "Minor"):  # §4 item 2
        for p in AGENT_RUNS + BASELINES:
            t.add("issues_by_level", lv, p, pol[p]["issues_by_level"].get(lv, 0), "gate" if lv == "Critical"
                  else "secondary", True, "explanation and process items do not apply to baselines (§4 item 1)")

    levels = ("Critical", "Major", "Moderate", "Minor")    # §4 item 2: lexicographic, most severe first
    counts = {p: tuple(pol[p]["issues_by_level"].get(lv, 0) for lv in levels) for p in pol}
    for r in AGENT_RUNS:
        for b in BASELINES:
            t.add("issues_lex", f"issue counts (Critical, Major, Moderate, Minor) vs {b}", r,
                  lexicographic(counts[r], counts[b]), "secondary", True,
                  "lower is better; read Critical first (§4 'Use in evaluation' item 2)")
    for p in AGENT_RUNS + BASELINES:                       # what the Moderate counts consist of
        days = audit_days(p if p in AGENT_RUNS else f"{p}-{PRIMARY}")
        by_type = Counter(i["type"] for d in days for i in d["issues"] if i["level"] == "Moderate")
        t.add("moderate_issues", "nurse_gap issues (days with a net nurse gap at tier 2 or 1 only)", p,
              by_type.get("nurse_gap", 0), "secondary", False, "audit issue type nurse_gap, level Moderate")
        t.add("moderate_issues", "other Moderate issues", p, sum(by_type.values()) - by_type.get("nurse_gap", 0),
              "secondary", False, ", ".join(f"{k} {v}" for k, v in sorted(by_type.items()) if k != "nurse_gap")
              or "none")

    labels = [x[0] for x in rows["R1"]]
    for p in rows:
        if [x[0] for x in rows[p]] != labels:
            raise SystemExit(f"{p}: metric rows differ")
    identical = {r: True for r in AGENT_RUNS}
    for i, label in enumerate(labels):
        role = rows["R1"][i][1]
        floors = {rows[p][i][3] for p in rows}
        if len(floors) != 1:
            print(f"STOP: floor of {label} differs between policies: {floors}")
            sys.exit(2)
        floor = rows["R1"][i][3]
        val = {p: rows[p][i][2] for p in rows}
        tab = TABLE[role]
        for p in AGENT_RUNS + BASELINES:
            t.add(tab, label, p, val[p], role, True)
        t.add(tab, label, "floor", floor, role, True, "policy-independent; a floor of 0 is a lower bound (§8)")
        for r in AGENT_RUNS:
            identical[r] &= val[r] == val["B1"]
        runs = [val[r] for r in AGENT_RUNS]
        t.add("main_variability", label, "min", min(runs), role, True, "§9")
        t.add("main_variability", label, "max", max(runs), role, True, "§9")
        t.add("main_variability", label, "mean", round(sum(runs) / 3, 4), role, True, "§9: mean over R1-R3")
        if role == "headline":
            for r in AGENT_RUNS:
                t.add("main_gap", label, f"{r} - B1", round(val[r] - val["B1"], 4), role, True, "gap to B1 (§1)")
            if floor is not None:
                for r in AGENT_RUNS:
                    t.add("main_gap", label, f"{r} - floor", round(val[r] - floor, 4), role, True,
                          "gap to the floor (§1)")
    for r, same in identical.items():
        if same:
            print(f"STOP: {r} equals B1 on every metric; check the pipeline before reporting")
            sys.exit(2)

    head = [(i, x[0]) for i, x in enumerate(rows["R1"]) if x[1] == "headline"]
    for metric in ("A1", "A2", "A3"):                      # a summary of the main_gap table, for the text
        idx = [i for i, label in head if label.startswith(metric)]
        for r in AGENT_RUNS:
            n = sum(1 for i in idx if round(rows[r][i][2] - rows["B1"][i][2], 9) != 0)
            t.add("main_gap_summary", f"{metric} rows with a non-zero gap to B1", r, frac(n, len(idx)), "headline",
                  False, "count of the main_gap rows of this metric")

    alloc = {r: final_allocations(r) for r in AGENT_RUNS}  # §9 decision-level agreement (Log #131)
    for a, b in ((AGENT_RUNS[0], AGENT_RUNS[1]), (AGENT_RUNS[0], AGENT_RUNS[2]), (AGENT_RUNS[1], AGENT_RUNS[2])):
        days = sorted(alloc[a])
        if days != sorted(alloc[b]) or len(days) != 30:
            raise SystemExit(f"{a}/{b}: allocation days differ")
        for res in ("beds", "nurses"):
            dist = [sum(abs(alloc[a][d][res][k] - alloc[b][d][res][k]) for k in alloc[a][d][res]) for d in days]
            note = "§9 names the quantity; this form was fixed after the runs (owner, 2026-11-24): descriptive"
            t.add("agreement", f"{a}-{b} {res}", "identical days", frac(sum(x == 0 for x in dist), len(days)),
                  "descriptive", False, note)
            t.add("agreement", f"{a}-{b} {res}", "mean L1 distance", round(sum(dist) / len(days), 4),
                  "descriptive", False, note + "; per day the sum over departments of |x_d - y_d|")

    for r in AGENT_RUNS:                                   # A2 lexicographic (§3.2)
        tri = lambda p: tuple(pol[p]["A2"][f"tier{j}"]["SV_N"] for j in (3, 2, 1))  # noqa: E731
        for b in BASELINES:
            t.add("main_lex", f"A2 (tier 3, 2, 1) vs {b}", r, lexicographic(tri(r), tri(b)), "headline", True,
                  "lower is better; read tier 3 first (§3.2)")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ANALYSIS_DIR))
    out = Table.write(build(), Path(ap.parse_args().out) / "main_comparison.csv")
    print(f"wrote {out}")
