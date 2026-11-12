"""Launch (or resume) the active run in a headless run session. The same command for the dry run and R1–R3:

    uv run python -m src.mcp_server.launch

Starts `claude -p "Start." --agent dispatcher --settings .claude/run-settings.json` from the project root
(CLAUDE.md §9.1). The model comes from the run settings (owner decision §11 #31); it is also passed to the
subagents through CLAUDE_CODE_SUBAGENT_MODEL, so an environment variable in the user's shell cannot change
it. The transcript is streamed to <run>/transcripts/launch-<k>.jsonl line by line, so a killed launch keeps
what it had. After the session ends, the observed models are compared with run_manifest.json, the record
consistency check runs, and both go to <run>/launches.jsonl. Re-running the command resumes the run: the
dispatcher starts from get_workflow_status, and the server rebuilds every flag from the records.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from src.evaluation.dataset import ROOT

from .consistency import check
from .store import Store

PROMPT = "Start."


def observed_models(transcript_lines: list[str]) -> dict:
    main, used, cost, result = set(), set(), None, None
    for line in transcript_lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            main.add(ev.get("model"))
        if ev.get("type") == "result":
            result = ev
            used |= set((ev.get("modelUsage") or {}).keys())
            cost = ev.get("total_cost_usd")
    return {"main_session": sorted(m for m in main if m), "all_used": sorted(used), "total_cost_usd": cost,
            "final_result": None if result is None else {k: result.get(k) for k in ("subtype", "is_error",
                                                                                     "num_turns", "result")}}


def launch(store: Store, max_turns: int = 2000) -> dict:
    m = store.manifest()
    model = m["models"]["main"]
    tdir = store.alloc_dir / "transcripts"
    tdir.mkdir(exist_ok=True)
    k = len(list(tdir.glob("launch-*.jsonl"))) + 1
    tpath = tdir / f"launch-{k}.jsonl"
    env = dict(os.environ, CLAUDE_CODE_SUBAGENT_MODEL=m["models"]["subagents"])
    cmd = ["claude", "-p", PROMPT, "--agent", "dispatcher", "--settings", ".claude/run-settings.json",
           "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns)]
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    lines: list[str] = []
    with open(tpath, "w", encoding="utf-8", newline="\n") as out:
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8")
        for line in proc.stdout:
            out.write(line)
            out.flush()
            lines.append(line)
        proc.wait()
        stderr = proc.stderr.read()
    obs = observed_models(lines)
    expected = sorted({model, m["models"]["subagents"]})
    rec = {"launch": k, "started_at": started, "duration_s": round(time.monotonic() - t0, 1),
           "exit_code": proc.returncode, "expected_models": expected, "observed": obs,
           "models_match": obs["all_used"] == expected and obs["main_session"] == [model],
           "state_after": store.read_state(), "consistency_problems": check(store),
           "stderr_tail": stderr[-1500:]}
    with open(store.alloc_dir / "launches.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main() -> int:
    store = Store.active()
    rec = launch(store)
    print(json.dumps({k: rec[k] for k in ("launch", "exit_code", "duration_s", "models_match",
                                          "consistency_problems")}, indent=2))
    print("state:", rec["state_after"]["phase"], "day", rec["state_after"]["day"])
    return 0 if rec["exit_code"] == 0 and not rec["consistency_problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
