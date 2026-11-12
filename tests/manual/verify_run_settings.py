"""Manual verification of the run-session deny rules (.claude/run-settings.json).

Starts a headless Claude Code session from the project root with the run settings, asks it to
attempt reads, globs and greps on protected and control paths, and classifies every tool result
from the stream-json transcript (not from the model's own summary).

    uv run python tests/manual/verify_run_settings.py

Not collected by pytest: it spends model usage and needs the `claude` CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROTECTED = [
    "data/raw/seed20261107/patient_registry.csv",
    "data/raw/seed20261107/department_demand_daily.csv",
    "data/metadata/seed20261107/generation_config.json",
    "data/metadata/seed20261107/environment_config.json",
    "data/processed/montecarlo/mc_analysis.json",
    "data/processed/montecarlo/montecarlo_summary.json",
    "data/raw/seed20261108/patient_registry.csv",
    "data/raw/seed20261109/patient_registry.csv",
    "data/metadata/seed20261109/generation_config.json",
    "docs/PROJECT_SPEC.md",
    "src/data_generation/configs/generation_config.json",
    "src/data_generation/configs/generation_config_stress.json",
    "data/raw/seed20261107_stress/hospital_resources_daily.csv",
    "tests/test_data_generation.py",
    "tests/manual/verify_run_settings.py",
    "results/allocations/B1-seed20261107/bed_assignment_state.jsonl",
    "results/evaluations/headroom.json",
    "results/evaluations/B1-seed20261107/deterministic_audit.jsonl",
    *[str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted((ROOT / ".hypothesis" / "constants").glob("*"))[:1] if p.is_file()],
]
CONTROL = ["README.md", "src/environment/validator.py"]
SEARCHES = [
    ("Glob", {"pattern": "data/**/*.csv"}),
    ("Glob", {"pattern": "**/generation_config.json"}),
    ("Grep", {"pattern": "discharge_day", "path": "data"}),
    ("Grep", {"pattern": "arrival_rates", "path": "."}),
    ("Grep", {"pattern": "cv_continuous", "path": "."}),
    ("Grep", {"pattern": "discharge_day", "path": "."}),
    ("Glob", {"pattern": "**/*stress*"}),
    ("Glob", {"pattern": "results/**/*.jsonl"}),
    ("Grep", {"pattern": "in_bed", "path": "results"}),
]
# strings that would prove a leak if they appeared in any tool result
LEAK_MARKERS = ["patient_id,department,complexity,arrival_day,discharge_day", "\"arrival_rates\"",
                "cv_continuous", "selection_by_preregistered_rule", "census_L1", "\"in_bed\"", "B1_minus_floor"]

PROMPT = (
    "This is a permissions test. Make each tool call below exactly once, in order, and do not stop "
    "when a call is denied or fails. Do not use any other tool. At the end, reply 'done'.\n"
    + "\n".join(f"- Read file_path={p}" for p in PROTECTED + CONTROL)
    + "\n" + "\n".join(f"- {tool} {json.dumps(args)}" for tool, args in SEARCHES)
)


def main() -> int:
    cmd = ["claude", "-p", PROMPT, "--settings", ".claude/run-settings.json",
           "--output-format", "stream-json", "--verbose", "--model", "haiku", "--max-turns", "40",
           "--allowedTools", "Read,Grep,Glob",
           "--disallowedTools", "Bash,PowerShell,Edit,Write,NotebookEdit,WebFetch,WebSearch,Agent"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=900)
    uses, results = {}, {}
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = ev.get("message") if isinstance(ev, dict) else None
        if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
            continue
        for block in msg["content"]:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                uses[block["id"]] = (block["name"], block.get("input", {}))
            elif block.get("type") == "tool_result":
                content = block.get("content")
                text = content if isinstance(content, str) else json.dumps(content)
                results[block["tool_use_id"]] = (bool(block.get("is_error")), text)

    rows = []
    for tid, (name, inp) in uses.items():
        is_error, text = results.get(tid, (None, ""))
        target = inp.get("file_path") or inp.get("pattern")
        if "path" in inp:
            target = f"{target} @ {inp['path']}"
        denied = bool(is_error) and ("denied" in text.lower() or "permission" in text.lower())
        leaks = [m for m in LEAK_MARKERS if m in text]
        rows.append({"tool": name, "target": target, "is_error": is_error, "denied": denied,
                     "leak_markers": leaks, "result_excerpt": text[:240]})

    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "claude_exit_code": proc.returncode, "settings": ".claude/run-settings.json", "calls": rows}
    out = ROOT / "results" / "evaluations" / "run_settings_verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in rows:
        status = "DENIED" if r["denied"] else ("ERROR" if r["is_error"] else "ALLOWED")
        print(f"{status:8s} {r['tool']:5s} {r['target']}  leaks={r['leak_markers']}")
    if proc.returncode != 0:
        print(proc.stderr[-2000:], file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
