"""Step 13: the STRESS1 probe, separate from the main comparison (PROJECT_SPEC.md §11 #74-#75;
EVALUATION_PLAN.md §2, §6 item 4, §8.2; Decisions Log #128).

    uv run python src/13_stress1.py [--out DIR]      # default: results/analysis/

Writes `<out>/stress1.csv`:

  stress_precondition  the shock-day A1 pairing against the closed form (§6 item 4: "Before any use, the
                       shock-day A1 pairing is tested against the closed form"), re-run here:
                       tests/test_environment_rest.py::test_pairing_equals_closed_form_shock_day (slow)
  stress_shock_days    per shock day and policy (STRESS1, B0-B2 on seed20261107_stress; shock day =
                       sum O_d > P_B, so it depends on each run's own holders): forced cut c(t), executed cut,
                       shock-cut pairs and severity, SHOCK_OVERCUT rejected and in effect, gate D components
                       of the day, and the criterion "follows the cut rule" (§11 #74)
  stress_criterion     days meeting the criterion / shock days, and the failing days with their type
  stress_metrics       the full §8.2 table, descriptive, with run-level gate D
  checker_STRESS1 / checker_STRESS1_shock / checker_STRESS1_nonshock
                       the CHECKER against the audit, same procedure as R1-R3 (src/11), descriptive, with shock
                       days as their own stratum (§11 #75); never pooled with R1-R3
Framing (§11 #74): one constructed probe (n = 1), reported as a case.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import ANALYSIS_DIR, BASELINES, STRESS, Table, audit_days, metric_rows, policy_metrics  # noqa: E402
from src.evaluation.checker_matching import match  # noqa: E402

_spec = importlib.util.spec_from_file_location("step11", ROOT / "src" / "11_checker_vs_audit.py")
step11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step11)

RUN = "STRESS1"
POLICIES = [RUN] + [f"{b}-{STRESS}" for b in BASELINES]
SHORT = {p: p.split("-")[0] for p in POLICIES}
PRECONDITION = "tests/test_environment_rest.py::test_pairing_equals_closed_form_shock_day"


def precondition() -> tuple[str, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-m", "slow or not slow", "-p", "no:cacheprovider",
                        PRECONDITION], cwd=ROOT, capture_output=True, text=True)
    last = [x for x in r.stdout.strip().splitlines() if x.strip()][-1]
    last = re.sub(r" in [0-9.]+s.*$", "", last)            # drop the timing, so the file is reproducible
    return ("passed" if r.returncode == 0 else "FAILED"), last


def overcut_rejected(run: str) -> int | None:
    """Rejected submissions whose codes include SHOCK_OVERCUT (decision_history.jsonl); None for baselines,
    which make no submissions."""
    p = ROOT / "results" / "allocations" / run / "decision_history.jsonl"
    if not p.exists():
        return None
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {d: sum(1 for x in rows if x["day"] == d and x["outcome"] == "rejected"
                   and any("SHOCK_OVERCUT" in c for c in x.get("codes") or [])) for d in {x["day"] for x in rows}}


def overcut_in_effect(errors: list[str]) -> bool:
    for e in errors:
        m = re.match(r"relaxed no-eviction: (\d+) cut, shortfall (\d+)", e)
        if m and int(m.group(1)) > int(m.group(2)):
            return True
    return False


def build() -> Table:
    t = Table()
    status, line = precondition()
    if status != "passed":
        print(f"STOP: precondition test failed: {line}")
        sys.exit(2)
    t.add("stress_precondition", "shock-day A1 pairing = closed form (Hypothesis property test)", "result",
          status, "check", True, f"{PRECONDITION}: {line}")

    for p in POLICIES:
        rej = overcut_rejected(p)
        days = [d for d in audit_days(p) if d["shock_day"]]
        meeting, failing = 0, []
        for d in days:
            day = d["day"]
            c = sum(d["occupied"].values()) - d["pool_beds"]
            cut = sum(max(0, d["occupied"][k] - d["beds"][k]) for k in d["beds"])
            sc = [x for x in d["pairs"] if x["kind"] == "shock_cut"]
            in_eff = overcut_in_effect(d["hard_constraint_errors"])
            mism = sum(1 for i in d["issues"] if i["type"] == "pairing_closed_form_mismatch")
            row = f"day {day}"
            col = SHORT[p]
            tab = "stress_shock_days"
            pre = p == RUN
            t.add(tab, f"{row} forced cut c(t)", col, c, "primary" if pre else "reference", True)
            t.add(tab, f"{row} executed cut", col, cut, "primary" if pre else "reference", True)
            t.add(tab, f"{row} shock-cut pairs", col, len(sc), "primary" if pre else "reference", True)
            t.add(tab, f"{row} shock-cut severity", col, sum(x["severity"] for x in sc),
                  "primary" if pre else "reference", True)
            t.add(tab, f"{row} SHOCK_OVERCUT rejected", col, None if rej is None else rej.get(day, 0),
                  "primary" if pre else "reference", True, "baselines make no submissions" if rej is None else "")
            t.add(tab, f"{row} SHOCK_OVERCUT in effect", col, in_eff, "primary" if pre else "reference", True)
            t.add(tab, f"{row} hard-constraint errors", col, len(d["hard_constraint_errors"]),
                  "primary" if pre else "reference", True)
            t.add(tab, f"{row} replay ok", col, d["replay_ok"], "primary" if pre else "reference", True)
            t.add(tab, f"{row} pairing / closed-form mismatches", col, mism, "primary" if pre else "reference", True)
            reasons = [r for r, bad in (("SHOCK_OVERCUT in effect", in_eff), ("executed cut != c(t)", cut != c),
                                        ("hard-constraint error", bool(d["hard_constraint_errors"])),
                                        ("replay mismatch", not d["replay_ok"]),
                                        ("pairing mismatch", mism > 0)) if bad]
            t.add(tab, f"{row} follows the cut rule", col, not reasons, "primary" if pre else "reference", True,
                  "; ".join(reasons))
            meeting += not reasons
            if reasons:
                failing.append(f"day {day}: {'; '.join(reasons)}")
        t.add("stress_criterion", "days meeting the criterion / shock days", SHORT[p], f"{meeting}/{len(days)}",
              "primary" if p == RUN else "reference", True, "; ".join(failing) or "no failing day")
        all_days = audit_days(p)                           # owner check 2026-11-24: shock days per policy
        t.add("stress_shock_day_count", "shock days", SHORT[p], len(days), "descriptive", False,
              "sum O_d > P_B, from each run's own holders")
        t.add("stress_shock_day_count", "shock days (list)", SHORT[p], " ".join(str(d["day"]) for d in days) or "none",
              "descriptive", False)
        changes = [d for prev, d in zip(all_days, all_days[1:]) if d["pool_beds"] != prev["pool_beds"]]
        t.add("stress_shock_day_count", "days with a bed-pool change", SHORT[p],
              " ".join(f"{d['day']}" for d in changes), "context", False, "dataset pools; equal for every policy")
        near = {c["day"] + k for c in changes for k in (-1, 0, 1)}   # each pool change with the days around it
        for d in all_days:
            if d["day"] in near:
                t.add("stress_pool_context", f"day {d['day']}", f"{SHORT[p]} pool / occupied",
                      f"{d['pool_beds']} / {sum(d['occupied'].values())}", "context", False,
                      "occupied = holders O at the start of the day; shock day if occupied > pool")

    pol = {SHORT[p]: policy_metrics(p, STRESS) for p in POLICIES}
    rows = {k: metric_rows(m) for k, m in pol.items()}
    if all(rows[RUN][i][2] == rows["B1"][i][2] for i in range(len(rows[RUN]))):
        print("STOP: STRESS1 equals B1 on every metric; check the pipeline before reporting")
        sys.exit(2)
    for k in pol:
        t.add("stress_metrics", "gate passed (run level)", k, pol[k]["D"]["gate_passed"], "descriptive", True)
    for i, (label, _, _, floor) in enumerate(rows[RUN]):
        if len({rows[k][i][3] for k in rows}) != 1:
            print(f"STOP: floor of {label} differs between policies")
            sys.exit(2)
        for k in pol:
            t.add("stress_metrics", label, k, rows[k][i][2], "descriptive", True, "§8.2 table; never pooled with R1-R3")
        t.add("stress_metrics", label, "floor", floor, "descriptive", True)

    audit, checker = step11.inputs(RUN)
    m = match(audit, checker, counts=True)
    step11.check_recount(RUN, audit, checker, m)
    step11.add_matching(t, "checker_STRESS1", m, role="descriptive")
    shock = {d["day"] for d in audit_days(RUN) if d["shock_day"]}
    for name, days in (("checker_STRESS1_shock", shock), ("checker_STRESS1_nonshock", set(range(1, 31)) - shock)):
        a, c = step11.inputs(RUN, days)
        ms = match(a, c, counts=True)
        step11.check_recount(RUN, a, c, ms)
        step11.add_matching(t, name, ms, role="descriptive")
        t.add("checker_STRESS1_extra", f"{name}: days", "value", " ".join(map(str, sorted(days))) if len(days) < 5
              else f"{len(days)} days", "descriptive", True)
        t.add("checker_STRESS1_extra", f"{name}: CHECKER LLM-only issues", "value",
              sum(ms["checker_llm_only"].values()), "descriptive", True,
              " ".join(f"{k} {v}" for k, v in sorted(ms["checker_llm_only"].items())) or "none")
    t.add("checker_STRESS1_extra", "date-shift matches (1-2 days)", "value", len(m["date_shift_matches"]),
          "descriptive", True)
    for ty in ("explanation_inaccuracy", "information_leak", "inconsistency", "other"):
        t.add("checker_STRESS1_extra", f"CHECKER LLM-only issues: {ty}", "value", m["checker_llm_only"].get(ty, 0),
              "descriptive", True, "explanation claims of STRESS1 are not scored (§4 item 5)")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ANALYSIS_DIR))
    out = Table.write(build(), Path(ap.parse_args().out) / "stress1.csv")
    print(f"wrote {out}")
