"""Per-run report from the records and the launch transcripts (dry run, R1–R3). Deterministic.

    uv run python -m src.evaluation.run_report <run_id>

Per day: the attempts and which was accepted, the what-if calls, the accepted allocation, and the audit
issues. Then the CHECKER reports, matched against the audit (checker_matching), and the tokens, wall-clock
time and cost, extrapolated to a 30-day run. Writes results/evaluations/<run_id>/run_report.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from src.evaluation.audit import audit_run
from src.evaluation.checker_matching import match
from src.evaluation.dataset import ROOT, load_dataset
from src.evaluation.metrics import add_reversal_issues
from src.mcp_server.store import Store

AGENT = {"Agent", "Task"}


def _transcript_events(alloc_dir: Path):
    for t in sorted((alloc_dir / "transcripts").glob("launch-*.jsonl")):
        for line in t.read_text(encoding="utf-8").splitlines():
            try:
                yield t.name, json.loads(line)
            except json.JSONDecodeError:
                continue


def transcript_stats(alloc_dir: Path) -> dict:
    """Maps each subagent invocation to its day (the number of successful advance_day calls before it)."""
    uses, results, notif, final, inits = {}, {}, {}, {}, []
    order = []
    for name, ev in _transcript_events(alloc_dir):
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            inits.append(ev.get("model"))
        if ev.get("type") == "system" and ev.get("subtype") == "task_notification":
            notif[ev.get("tool_use_id")] = ev.get("usage") or {}
        if ev.get("type") == "result":
            final[name] = ev
        msg = ev.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
            continue
        for b in msg["content"]:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                uses[b["id"]] = {"name": b["name"], "input": b.get("input", {}), "parent": ev.get("parent_tool_use_id")}
                order.append(b["id"])
            elif isinstance(b, dict) and b.get("type") == "tool_result":
                results[b["tool_use_id"]] = bool(b.get("is_error"))
    day, task_day, task_role = 0, {}, {}
    for tid in order:
        u = uses[tid]
        if u["parent"] is None:
            if u["name"] == "mcp__orchestration__advance_day" and results.get(tid) is False:
                day += 1
            if u["name"] in AGENT:
                task_day[tid], task_role[tid] = day, u["input"].get("subagent_type")
    per_day = defaultdict(lambda: {"allocator_invocations": 0, "simulate_calls": 0, "validate_calls": 0,
                                   "tool_errors": 0, "allocator_tokens": 0, "allocator_duration_s": 0.0,
                                   "checker_tokens": 0, "checker_duration_s": 0.0})
    for tid, u in uses.items():
        p = u["parent"]
        if p in task_day:
            d = per_day[task_day[p]]
            if u["name"].endswith("__simulate_allocation") and task_role[p] == "allocator":
                d["simulate_calls"] += 1
            if u["name"].endswith("__validate_allocation"):
                d["validate_calls"] += 1
            if results.get(tid):
                d["tool_errors"] += 1
    for tid, t in task_day.items():
        d, usage = per_day[t], notif.get(tid, {})
        role = task_role[tid]
        if role == "allocator":
            d["allocator_invocations"] += 1
        d[f"{role}_tokens"] += usage.get("total_tokens", 0)
        d[f"{role}_duration_s"] += round(usage.get("duration_ms", 0) / 1000, 1)
    costs = {n: e.get("total_cost_usd") for n, e in final.items()}
    model_usage = {n: e.get("modelUsage") for n, e in final.items()}
    return {"per_day": {k: dict(v) for k, v in sorted(per_day.items())}, "session_cost_usd": costs,
            "model_usage": model_usage, "main_models": sorted(set(m for m in inits if m))}


def _ts(x: str) -> datetime:
    return datetime.fromisoformat(x)


def build(run_id: str) -> dict:
    alloc = ROOT / "results" / "allocations" / run_id
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    store = Store(alloc, Path(m["eval_dir"]))
    ds = load_dataset(m["dataset_id"], root=Path(m["data_root"]))
    _, days = audit_run(ds, alloc)
    add_reversal_issues(days)
    tr = transcript_stats(alloc)
    wf = store.read("workflow")
    dec = store.read("decision_history")
    allocs = store.read("allocation_state")
    out_days = []
    for d in days:
        t = d["day"]
        tdec = [x for x in dec if x["day"] == t]
        acc = [x for x in tdec if x["outcome"] == "accepted"]
        ev = {x["event"]: x["created_at"] for x in wf if x["day"] == t and x["event"] in ("advance_day", "close_day")}
        wall = (_ts(ev["close_day"]) - _ts(ev["advance_day"])).total_seconds() if len(ev) == 2 else None
        final = [x for x in allocs if x["day"] == t and x["source"] != "initial_rule"][-1]
        out_days.append({
            "day": t, "attempts": len(tdec), "accepted_on_attempt": acc[0]["attempt"] if acc else None,
            "rejection_codes": [x["codes"] for x in tdec if x["outcome"] == "rejected"],
            "source": final["source"], "beds": final["beds"], "nurses": final["nurses"],
            "audit_issues": dict(Counter(f'{i["type"]} ({i["level"]})' for i in d["issues"])),
            "wall_clock_s": wall, **tr["per_day"].get(t, {})})
    audit_issues = [i for d in days for i in d["issues"]]
    reports = [x for x in store.read("validation_history")]
    matching = []
    for r in reports:
        if r.get("kind") != "report":
            matching.append({"day": r["day"], "kind": r.get("kind")})
            continue
        lo, hi = r["report"]["period"]["from_day"], r["report"]["period"]["to_day"]
        ai = [i for i in audit_issues if lo <= i["day"] <= hi]
        matching.append({"day": r["day"], "period": [lo, hi], "n_issues": len(r["report"]["issues"]),
                         "checker_types": dict(Counter(i.get("type") for i in r["report"]["issues"])),
                         **match(ai, r["report"]["issues"])})
    rep = {"run_id": run_id, "models_configured": m["models"], "main_models_observed": tr["main_models"],
           "model_usage": tr["model_usage"], "session_cost_usd": tr["session_cost_usd"],
           "days": out_days, "checker": matching}
    (Path(m["eval_dir"]) / "run_report.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8",
                                                         newline="\n")
    return rep


if __name__ == "__main__":
    r = build(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("run_id", "models_configured", "main_models_observed",
                                        "session_cost_usd")}, indent=2))
