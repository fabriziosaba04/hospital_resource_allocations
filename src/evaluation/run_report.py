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
from src.utils.paths import guard_write, long_path, recomputed_dir

AGENT = {"Agent", "Task"}


def _transcript_events(alloc_dir: Path):
    def launch_no(t: Path) -> int:                     # launch-10 after launch-9, not after launch-1
        return int(t.stem.split("-")[-1])
    for t in sorted((alloc_dir / "transcripts").glob("launch-*.jsonl"), key=launch_no):
        for line in t.read_text(encoding="utf-8").splitlines():
            try:
                yield t.name, json.loads(line)
            except json.JSONDecodeError:
                continue


def transcript_stats(alloc_dir: Path) -> dict:
    """Maps each subagent invocation to its day: the day reported by the last orchestration tool result before
    it (get_workflow_status, advance_day, ...), so a launch cut off by a usage limit and resumed in a new launch
    keeps the right day even if a tool result was lost (Log #92)."""
    uses, results, notif, final, inits, reported_day = {}, {}, {}, {}, [], {}
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
                if ev.get("parent_tool_use_id") is None and not b.get("is_error"):
                    for blk in b.get("content") if isinstance(b.get("content"), list) else []:
                        try:
                            obj = json.loads(blk.get("text", ""))
                        except (json.JSONDecodeError, TypeError, AttributeError):
                            continue
                        if isinstance(obj, dict) and isinstance(obj.get("day"), int):
                            reported_day[b["tool_use_id"]] = obj["day"]
    day, task_day, task_role = 0, {}, {}
    for tid in order:
        u = uses[tid]
        if u["parent"] is None:
            if tid in reported_day:
                day = reported_day[tid]
            elif u["name"] == "mcp__orchestration__advance_day" and results.get(tid) is False:
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
    # a launch cut off before its final result has no reported cost: listed as None, never left out (Log #96)
    names = sorted((t.name for t in (alloc_dir / "transcripts").glob("launch-*.jsonl")),
                   key=lambda n: int(n.split("-")[-1].split(".")[0]))
    costs = {n: final[n].get("total_cost_usd") if n in final else None for n in names}
    model_usage = {n: e.get("modelUsage") for n, e in final.items()}
    return {"per_day": {k: dict(v) for k, v in sorted(per_day.items())}, "session_cost_usd": costs,
            "model_usage": model_usage, "main_models": sorted(set(m for m in inits if m))}


def _ts(x: str) -> datetime:
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def launch_intervals(alloc_dir: Path) -> list[tuple[datetime, datetime]]:
    """[first, last] message timestamp of each launch transcript. A launch killed by a usage limit keeps what it
    streamed, so its interval ends at its last recorded message (Log #96)."""
    spans = {}
    for name, ev in _transcript_events(alloc_dir):
        ts = ev.get("timestamp") if isinstance(ev, dict) else None
        if isinstance(ts, str):
            t = _ts(ts)
            lo, hi = spans.get(name, (t, t))
            spans[name] = (min(lo, t), max(hi, t))
    return sorted(spans.values())


def active_seconds(start: datetime, end: datetime, intervals) -> tuple[float, int]:
    """Seconds of [start, end] that fall inside some launch, and the number of launches it touches. Without
    transcript timestamps the whole span is returned (single-launch runs before Log #96)."""
    if not intervals:
        return (end - start).total_seconds(), 1
    total, n = 0.0, 0
    for lo, hi in intervals:
        a, b = max(start, lo), min(end, hi)
        if a <= b:
            total += (b - a).total_seconds()
            n += 1
    return total, n


def resolve_data_root(m: dict, data_root: Path | None = None) -> Path:
    """The dataset root for a run: an explicit override, else the manifest's `data_root` if it exists (a
    clone may have been deleted), else the repository root (frozen data are identical by manifest).
    A synthetic fixture recorded under the old `results/dry_runs/` (moved by the clean-up of 2026-11-23, or on
    another machine) resolves to `results/development/dry_runs/<fixture>`; the records are never edited."""
    if data_root is not None:
        return Path(data_root)
    p = Path(m["data_root"])
    if p.exists():
        return p
    parts = [x for x in str(m["data_root"]).replace("\\", "/").split("/") if x]
    if "dry_runs" in parts:
        moved = ROOT.joinpath("results", "development", "dry_runs", *parts[parts.index("dry_runs") + 1:])
        if moved.exists():
            return moved
    return ROOT


def build(run_id: str, results_root: Path = ROOT / "results", data_root: Path | None = None,
          write: bool = True, out_dir: Path | None = None) -> dict:
    """Paths are resolved relative to `results_root` (owner decision §11 #44, Log #90), so a run folder
    copied back from a clone gives the same report as in place. The report goes to `out_dir`, by default
    `<results_root>/analysis/recomputed/<run_id>/`; only copy-back passes the run's own evaluation folder
    (owner decision 2026-11-23, R59)."""
    alloc = long_path(Path(results_root) / "allocations" / run_id)     # Log #117
    m = json.loads((alloc / "run_manifest.json").read_text(encoding="utf-8"))
    store = Store.from_run_dir(alloc)
    ds = load_dataset(m["dataset_id"], root=resolve_data_root(m, data_root))
    _, days = audit_run(ds, alloc)
    add_reversal_issues(days)
    tr = transcript_stats(alloc)
    spans = launch_intervals(alloc)
    wf = store.read("workflow")
    dec = store.read("decision_history")
    allocs = store.read("allocation_state")
    out_days = []
    for d in days:
        t = d["day"]
        tdec = [x for x in dec if x["day"] == t]
        acc = [x for x in tdec if x["outcome"] == "accepted"]
        ev = {x["event"]: x["created_at"] for x in wf if x["day"] == t and x["event"] in ("advance_day", "close_day")}
        # wall clock = time inside a launch between advance_day and close_day; the gap between a cut-off launch
        # and its resume is not the day's work (Log #96). The raw span is kept as elapsed_s.
        if len(ev) == 2:
            a, b = _ts(ev["advance_day"]), _ts(ev["close_day"])
            wall, n_launches = active_seconds(a, b, spans)
            elapsed = (b - a).total_seconds()
        else:
            wall = elapsed = n_launches = None
        final = [x for x in allocs if x["day"] == t and x["source"] != "initial_rule"][-1]
        out_days.append({
            "day": t, "attempts": len(tdec), "accepted_on_attempt": acc[0]["attempt"] if acc else None,
            "rejection_codes": [x["codes"] for x in tdec if x["outcome"] == "rejected"],
            "source": final["source"], "beds": final["beds"], "nurses": final["nurses"],
            "audit_issues": dict(Counter(f'{i["type"]} ({i["level"]})' for i in d["issues"])),
            "wall_clock_s": wall, "elapsed_s": elapsed, "launches": n_launches, **tr["per_day"].get(t, {})})
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
    reps = [r for r in reports if r.get("kind") == "report"]
    covered = [i for i in audit_issues
               if any(r["report"]["period"]["from_day"] <= i["day"] <= r["report"]["period"]["to_day"] for r in reps)]
    overall = match(covered, [i for r in reps for i in r["report"]["issues"]]) if reps else None
    calls = store.read("process_calls")                  # owner decision §11 #39: descriptive process data
    for od in out_days:
        mine = [c for c in calls if c["day"] == od["day"] and c["writer"] == "allocator"]
        od["allocator_calls"] = dict(Counter(c["tool"] for c in mine))
    rep = {"run_id": run_id, "models_configured": m["models"], "main_models_observed": tr["main_models"],
           "model_usage": tr["model_usage"], "session_cost_usd": tr["session_cost_usd"],
           "days": out_days, "checker": matching, "checker_overall": overall,
           "checker_simulate_calls": sum(1 for c in calls if c["writer"] == "checker")}
    if write:
        out = long_path(guard_write(Path(out_dir) if out_dir is not None
                                    else recomputed_dir(run_id, results_root)))
        out.mkdir(parents=True, exist_ok=True)
        (out / "run_report.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rep


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("--results-root", default=str(ROOT / "results"))
    ap.add_argument("--data-root")
    ap.add_argument("--out", help="output folder (default results/analysis/recomputed/<run_id>/)")
    a = ap.parse_args()
    r = build(a.run_id, Path(a.results_root), Path(a.data_root) if a.data_root else None,
              out_dir=Path(a.out) if a.out else None)
    print(json.dumps({k: r[k] for k in ("run_id", "models_configured", "main_models_observed",
                                        "session_cost_usd")}, indent=2))
