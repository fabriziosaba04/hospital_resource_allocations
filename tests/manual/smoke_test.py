"""Smoke test (AGENTS.md §2.4), on the synthetic SMOKE5 fixture only. Never touches the frozen datasets.

    uv run python tests/manual/smoke_test.py

Two headless sessions, both started from the project root with the real run settings:

1. **Run session:** `--agent dispatcher`, exactly as a real run. The dispatcher runs its normal loop over
   the 5-day fixture (it refuses off-protocol instructions, R22), so the ALLOCATOR and CHECKER act with
   their real prompts on synthetic data.
2. **Spawn probe (check 5c):** `tests/manual/fixtures/spawn-probe.md` (frontmatter identical to
   `dispatcher.md` except the name) is copied into `.claude/agents/` only for this session, told to spawn
   an `Explore` subagent, and removed afterwards; its SHA-256 is recorded (owner decision §11 #30).

Every check is classified from the stream-json transcripts and the run's own records, not from a model's
summary. Not collected by pytest: it spends model usage (haiku) and needs the `claude` CLI.
"""

from __future__ import annotations

import hashlib
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

AGENT_TOOL = {"Agent", "Task"}          # the stream-json init event names the Agent tool "Task" (claude 2.1.322)
PROBE_SRC = ROOT / "tests" / "manual" / "fixtures" / "spawn-probe.md"
PROBE_DST = ROOT / ".claude" / "agents" / "spawn-probe.md"
RUN_PROMPT = "Start."
PROBE_PROMPT = "Run the probe described in your instructions."
LABEL_KEYS = ("bed_priority_violations", "nurse_priority_gap_by_tier", "\\\"severity\\\"", "unserved_level")
AUDIT_KEYS = ("bed_gap", "nurse_lex_floor_h", "nurse_net_h", "f1_inversions", "tau_beds", "bed_floor",
              "hard_constraint_errors")


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
    agent_ids = {tid: u["input"].get("subagent_type") for tid, u in uses.items() if u["name"] in AGENT_TOOL}
    calls = []
    for tid, u in uses.items():
        err, text = results.get(tid, (None, ""))
        calls.append({"name": u["name"], "by": agent_ids.get(u["parent"], "?") if u["parent"] else "main",
                      "is_error": err, "excerpt": text[:300], "full_result": text,
                      "input": u["input"] if u["name"] in AGENT_TOOL else None})
    return {"init_tools": init.get("tools") if init else None,
            "init_mcp_servers": init.get("mcp_servers") if init else None, "calls": calls, "texts": texts,
            "final": final}


def run_claude(prompt: str, agent: str, env: dict) -> subprocess.CompletedProcess:
    cmd = ["claude", "-p", prompt, "--agent", agent, "--settings", ".claude/run-settings.json",
           "--output-format", "stream-json", "--verbose", "--model", "haiku", "--max-turns", "80"]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=2400, env=env)


def main() -> int:
    previous = POINTER.read_text(encoding="utf-8") if POINTER.exists() else None
    tmp = Path(tempfile.mkdtemp(prefix="hra-smoke-"))
    run_id = "SMOKE-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    env = dict(os.environ, CLAUDE_CODE_SUBAGENT_MODEL="haiku")
    checks: dict[str, bool] = {}
    out_dir = ROOT / "results" / "evaluations"
    try:
        # ---------------------------------------------------------------- 1. run session
        write_fixture(tmp)
        store = init_run(DATASET_ID, run_id, data_root=tmp, results_root=tmp / "results", check_manifest=False)
        proc = run_claude(RUN_PROMPT, "dispatcher", env)
        (out_dir / "smoke_test_transcript.jsonl").write_text(proc.stdout, encoding="utf-8")
        rep = classify(proc.stdout)
        calls = rep["calls"]
        main_tools = set(rep["init_tools"] or [])
        orch = {f"mcp__orchestration__{t}" for t in ROLE_TOOLS["orchestration"]}

        def ok(by, name):
            return any(c["by"] == by and c["name"] == name and c["is_error"] is False for c in calls)

        def foreign_ok(by, prefixes):
            return [c["name"] for c in calls if c["by"] == by and c["is_error"] is False
                    and any(c["name"].startswith(p) for p in prefixes)]

        checks["1_allocator_called_every_own_tool"] = all(ok("allocator", f"mcp__allocator__{t}") for t in ROLE_TOOLS["allocator"])
        checks["1_allocator_no_foreign_tool_succeeded"] = not foreign_ok("allocator", ("mcp__checker__", "mcp__orchestration__"))
        checks["2_checker_called_every_own_tool"] = all(ok("checker", f"mcp__checker__{t}") for t in ROLE_TOOLS["checker"])
        checks["2_checker_no_foreign_tool_succeeded"] = not foreign_ok("checker", ("mcp__allocator__", "mcp__orchestration__"))
        checks["3_5_main_session_tools_exactly_orchestration_and_Agent"] = (
            len(main_tools & AGENT_TOOL) == 1 and main_tools - AGENT_TOOL == orch)
        checks["3_main_cannot_submit"] = not any("submit_" in t for t in main_tools)
        checks["5_main_has_no_read_write_edit_bash"] = not (main_tools & {"Read", "Write", "Edit", "Bash", "PowerShell", "Glob", "Grep"})
        checks["5_dispatcher_spawned_only_allocator_and_checker"] = all(
            (c["input"] or {}).get("subagent_type") in ("allocator", "checker")
            for c in calls if c["by"] == "main" and c["name"] in AGENT_TOOL)
        checks["4_inline_servers_connected"] = ok("allocator", "mcp__allocator__get_observed_state") and any(
            c["by"] == "checker" and c["name"].startswith("mcp__checker__") and c["is_error"] is False for c in calls)
        checks["4_orchestration_connected"] = any(s.get("name") == "orchestration" and s.get("status") == "connected"
                                                  for s in (rep["init_mcp_servers"] or []))
        # visibility (owner decision §11 #29)
        checks["vis_allocator_whatif_has_no_labels"] = not any(
            c["by"] == "allocator" and any(k in c["full_result"] for k in LABEL_KEYS) for c in calls)
        checks["vis_checker_sees_no_audit_content"] = not any(
            c["by"] == "checker" and any(k in c["full_result"] for k in AUDIT_KEYS) for c in calls)
        checks["vis_no_deterministic_audit_tool_called"] = not any("deterministic_audit" in c["name"] for c in calls)
        checks["vis_run_labels_flag_off"] = store.manifest()["expose_violation_labels"] is False
        # records
        state = store.read_state()
        checks["records_run_finished"] = state["phase"] == "FINISHED"
        checks["records_allocator_wrote_decision"] = any(x["writer"] == "allocator" and x["outcome"] == "accepted"
                                                         for x in store.read("decision_history"))
        checks["records_checker_wrote_report"] = any(x["writer"] == "llm_checker" and x["kind"] == "report"
                                                     for x in store.read("validation_history"))
        checks["records_one_audit"] = len(store.read("deterministic_audit")) == 1

        # ---------------------------------------------------------------- 2. spawn probe (check 5c)
        probe_hash = hashlib.sha256(PROBE_SRC.read_bytes()).hexdigest()
        if PROBE_DST.exists():
            raise SystemExit(f"{PROBE_DST} already exists; refusing to overwrite it")
        shutil.copyfile(PROBE_SRC, PROBE_DST)
        try:
            pproc = run_claude(PROBE_PROMPT, "spawn-probe", env)
        finally:
            PROBE_DST.unlink(missing_ok=True)
        (out_dir / "smoke_probe_transcript.jsonl").write_text(pproc.stdout, encoding="utf-8")
        prep = classify(pproc.stdout)
        spawns = [c for c in prep["calls"] if c["by"] == "main" and c["name"] in AGENT_TOOL]
        foreign = [c for c in spawns if (c["input"] or {}).get("subagent_type") not in ("allocator", "checker")]
        checks["5c_probe_tools_identical_to_dispatcher"] = set(prep["init_tools"] or []) == main_tools
        checks["5c_other_subagent_spawn_attempted_and_refused"] = bool(foreign) and all(c["is_error"] for c in foreign)
        checks["5c_no_subagent_ran_in_probe"] = not any(t["parent"] for t in prep["texts"]) and not any(
            c["by"] != "main" for c in prep["calls"])
        checks["5c_probe_file_removed"] = not PROBE_DST.exists()

        report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_id": run_id,
                  "claude_exit_codes": [proc.returncode, pproc.returncode], "checks": checks,
                  "passed": all(checks.values()), "main_session_tools": sorted(main_tools),
                  "mcp_servers": rep["init_mcp_servers"], "probe_fixture_sha256": probe_hash,
                  "probe_spawn_results": [{"input": c["input"], "is_error": c["is_error"], "result": c["excerpt"]}
                                          for c in spawns],
                  "probe_final": prep["final"], "run_final": rep["final"],
                  "calls": [{k: v for k, v in c.items() if k != "full_result"} for c in calls],
                  "texts": rep["texts"], "stderr_tail": (proc.stderr + pproc.stderr)[-1500:]}
        out = out_dir / "smoke_test.json"
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        for k, v in checks.items():
            print(f"{'PASS' if v else 'FAIL'}  {k}")
        print(f"record: {out}")
        return 0 if report["passed"] else 1
    finally:
        PROBE_DST.unlink(missing_ok=True)
        if previous is None:
            POINTER.unlink(missing_ok=True)
        else:
            POINTER.write_text(previous, encoding="utf-8")
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
