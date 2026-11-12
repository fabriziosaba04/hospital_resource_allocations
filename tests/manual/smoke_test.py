"""Smoke test (AGENTS.md §2.4), on the synthetic SMOKE5 fixture only. Never touches the frozen datasets.

    uv run python tests/manual/smoke_test.py

Starts one headless run session exactly as a real run would (`--agent dispatcher --settings
.claude/run-settings.json`, from the project root) and drives a 5-day run of the fixture with smoke
prompts: the subagents call their own tools mechanically and attempt forbidden ones; they make no
allocation judgement (day 1 re-submits the allocation in effect; days 2-4 fall back to the repair rule).
Classifies every tool call from the stream-json transcript and the run's own records, not from the
model's summary. Not collected by pytest: it spends model usage (haiku) and needs the `claude` CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.mcp_server.fixture import DATASET_ID, write_fixture  # noqa: E402
from src.mcp_server.init_run import init_run  # noqa: E402
from src.mcp_server.server import ROLE_TOOLS  # noqa: E402
from src.mcp_server.store import POINTER  # noqa: E402

EXPL = "situation, information_used, alternatives, reasons, tradeoffs, uncertainty each set to 'smoke test'"
ALLOC_SMOKE = (
    "SMOKE TEST on synthetic data; make no judgement. Call each of these tools once: get_observed_state, "
    "get_allocation_state, get_decision_history, get_overflow_queue. Then call simulate_allocation and "
    "validate_allocation with the beds and nurses currently in effect, then submit_decision with that same "
    f"allocation and an explanation with the fields {EXPL}. Then try to call the tools "
    "mcp__orchestration__advance_day and mcp__checker__submit_validation_report and say whether they exist. "
    "Finally list the exact names of every tool you have.")
CHECK_SMOKE = (
    "SMOKE TEST on synthetic data; make no judgement. Call get_deterministic_audit, get_decision_history and "
    "get_observed_state once each. Try to call mcp__allocator__submit_decision and mcp__orchestration__close_day "
    "and say whether they exist. Then call submit_validation_report with report = {\"period\": {\"from_day\": 1, "
    "\"to_day\": 5}, \"checked\": [\"smoke\"], \"issues\": [], \"summary\": \"smoke test\"}. "
    "Finally list the exact names of every tool you have.")
AGENT_TOOL = {"Agent", "Task"}
PROMPT = (
    "SMOKE TEST of the run setup on a synthetic 5-day fixture. For this session only, replace the normal loop "
    "with these steps, in order, and do not skip any:\n"
    "1. Call get_workflow_status, then advance_day.\n"
    f"2. Invoke the allocator subagent with exactly this prompt: {ALLOC_SMOKE}\n"
    "3. Call end_allocation_phase, then close_day.\n"
    "4. For each of days 2, 3 and 4: call advance_day, end_allocation_phase, close_day (no subagent).\n"
    "5. Day 5: call advance_day, then end_allocation_phase.\n"
    f"6. Invoke the checker subagent with exactly this prompt: {CHECK_SMOKE}\n"
    "7. Call close_day, then get_workflow_status.\n"
    "8. Try to invoke a subagent of type Explore with the prompt 'say hi', and note the result.\n"
    "9. Reply with the word done.")


def classify(stdout: str) -> dict:
    init, uses, results, texts, final = None, {}, {}, [], None
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init" and init is None:
            init = ev
        if ev.get("type") == "result":
            final = {k: ev.get(k) for k in ("subtype", "is_error", "num_turns", "result")}
        msg = ev.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
            continue
        for b in msg["content"]:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and ev.get("type") == "assistant":
                texts.append({"parent": ev.get("parent_tool_use_id"), "text": b.get("text", "")[:500]})
            if b.get("type") == "tool_use":
                uses[b["id"]] = {"name": b["name"], "input": b.get("input", {}), "parent": ev.get("parent_tool_use_id")}
            elif b.get("type") == "tool_result":
                c = b.get("content")
                results[b["tool_use_id"]] = (bool(b.get("is_error")), c if isinstance(c, str) else json.dumps(c))
    calls = []
    agent_ids = {}
    for tid, u in uses.items():
        if u["name"] in AGENT_TOOL:
            agent_ids[tid] = u["input"].get("subagent_type")
    for tid, u in uses.items():
        err, text = results.get(tid, (None, ""))
        calls.append({"name": u["name"], "by": agent_ids.get(u["parent"], "main") if u["parent"] else "main",
                      "is_error": err, "excerpt": text[:200], "input": u["input"] if u["name"] in AGENT_TOOL else None})
    return {"init_tools": init.get("tools") if init else None,
            "init_mcp_servers": init.get("mcp_servers") if init else None, "calls": calls, "texts": texts,
            "final": final}


def main() -> int:
    previous = POINTER.read_text(encoding="utf-8") if POINTER.exists() else None
    tmp = Path(tempfile.mkdtemp(prefix="hra-smoke-"))
    run_id = "SMOKE-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    checks: dict[str, bool] = {}
    try:
        write_fixture(tmp)
        store = init_run(DATASET_ID, run_id, data_root=tmp, results_root=tmp / "results", check_manifest=False)
        env = dict(os.environ, CLAUDE_CODE_SUBAGENT_MODEL="haiku")
        cmd = ["claude", "-p", PROMPT, "--agent", "dispatcher", "--settings", ".claude/run-settings.json",
               "--output-format", "stream-json", "--verbose", "--model", "haiku", "--max-turns", "80"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=1800, env=env)
        rep = classify(proc.stdout)
        calls = rep["calls"]
        main_tools = set(rep["init_tools"] or [])
        orch = {f"mcp__orchestration__{t}" for t in ROLE_TOOLS["orchestration"]}

        def ok(by, name):
            return any(c["by"] == by and c["name"] == name and c["is_error"] is False for c in calls)

        def succeeded_foreign(by, prefixes):
            return [c["name"] for c in calls if c["by"] == by and c["is_error"] is False
                    and any(c["name"].startswith(p) for p in prefixes)]

        # 1-2: each subagent can call all of its tools and no foreign tool succeeds
        checks["1_allocator_calls_all_own_tools"] = all(ok("allocator", f"mcp__allocator__{t}") for t in ROLE_TOOLS["allocator"])
        checks["1_allocator_no_foreign_tool_succeeded"] = not succeeded_foreign("allocator", ("mcp__checker__", "mcp__orchestration__"))
        checks["2_checker_calls_all_own_tools"] = all(ok("checker", f"mcp__checker__{t}") for t in ROLE_TOOLS["checker"])
        checks["2_checker_no_foreign_tool_succeeded"] = not succeeded_foreign("checker", ("mcp__allocator__", "mcp__orchestration__"))
        # 3, 5: the main session's tool set is exactly the orchestration tools plus Agent
        # the stream-json init event names the Agent tool "Task" (observed with claude 2.1.322)
        checks["3_5_main_session_tools_exactly_orchestration_and_Agent"] = (
            len(main_tools & AGENT_TOOL) == 1 and main_tools - AGENT_TOOL == orch)
        checks["3_main_cannot_submit"] = not any("submit_" in t for t in main_tools)
        checks["5_main_has_no_read_write_edit_bash"] = not (main_tools & {"Read", "Write", "Edit", "Bash", "PowerShell", "Glob", "Grep"})
        explore = [c for c in calls if c["by"] == "main" and c["name"] in AGENT_TOOL
                   and (c["input"] or {}).get("subagent_type") not in ("allocator", "checker")]
        checks["5_other_subagent_spawn_refused"] = bool(explore) and all(c["is_error"] for c in explore)
        # 4: inline role servers connected (their tools ran), orchestration server connected
        checks["4_inline_servers_connected"] = ok("allocator", "mcp__allocator__get_observed_state") and ok("checker", "mcp__checker__get_deterministic_audit")
        checks["4_orchestration_connected"] = any(s.get("name") == "orchestration" and s.get("status") == "connected"
                                                  for s in (rep["init_mcp_servers"] or []))
        # records: the run itself went through the state machine as expected
        state = store.read_state()
        dh = store.read("decision_history")
        vh = store.read("validation_history")
        checks["records_run_finished"] = state["phase"] == "FINISHED"
        checks["records_allocator_wrote_decision"] = any(x["writer"] == "allocator" and x["outcome"] == "accepted" for x in dh)
        checks["records_checker_wrote_report"] = any(x["writer"] == "llm_checker" and x["kind"] == "report" for x in vh)
        checks["records_one_audit"] = len(store.read("deterministic_audit")) == 1
        report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_id": run_id,
                  "claude_exit_code": proc.returncode, "checks": checks, "passed": all(checks.values()),
                  "main_session_tools": sorted(main_tools), "mcp_servers": rep["init_mcp_servers"],
                  "calls": calls, "texts": rep["texts"], "final": rep["final"], "stderr_tail": proc.stderr[-1500:]}
        (ROOT / "results" / "evaluations" / "smoke_test_transcript.jsonl").write_text(proc.stdout, encoding="utf-8")
        out = ROOT / "results" / "evaluations" / "smoke_test.json"
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        for k, v in checks.items():
            print(f"{'PASS' if v else 'FAIL'}  {k}")
        print(f"record: {out}")
        return 0 if report["passed"] else 1
    finally:
        if previous is None:
            POINTER.unlink(missing_ok=True)
        else:
            POINTER.write_text(previous, encoding="utf-8")
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
