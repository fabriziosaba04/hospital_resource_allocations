"""Copy a finished run back from a clone outside OneDrive into this repository (owner decision §11 #44, Log #90).

    uv run python -m src.mcp_server.copy_back <clone root> <run_id>

Copies **everything** the run wrote, both run folders in full: `results/allocations/<run>` (records,
`run_manifest.json`, `state.json`, `launches.jsonl`, `transcripts/`, any replay file) and
`results/evaluations/<run>` (`deterministic_audit.jsonl`, `validation_history.jsonl`, `process_calls.jsonl`,
reports). Then it
  1. verifies that the SHA-256 of every copied file equals the clone's;
  2. runs the record consistency check on the copy, with paths resolved relative to the copy;
  3. rebuilds the run report in the repository (`run_report.build`, data from the repository root when the
     clone's data root no longer exists; frozen data are identical by manifest);
  4. captures the per-subagent transcripts (R40, Log #103): for every session id in the run's
     `transcripts/launch-<k>.jsonl`, the folder `<projects>/*/<session id>/` that Claude Code wrote outside the
     run folder (`<projects>` = `$CLAUDE_CONFIG_DIR/projects`, default `~/.claude/projects`) is copied by
     `allocator_digest.preserve` into `results/allocations/<run>/transcripts/subagents/`, hash-checked. A launch
     that spawned subagents but whose session folder is missing (or found twice) is a capture problem;
  5. writes `results/evaluations/<run>/copy_back.json` with the hashes and the outcome.
It refuses to overwrite an existing run folder, and refuses a clone inside a synced folder only as a source
warning (the copy itself is harmless).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.dataset import ROOT

from .consistency import check
from .store import Store


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _files(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)).replace("\\", "/"): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def projects_root() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(base) if base else Path.home() / ".claude") / "projects"


def capture_subagents(run_alloc_dir: Path, run_id: str, repo_results: Path, projects: Path) -> dict:
    """Locate each launch's session folder and preserve its subagent transcripts (R40)."""
    from src.evaluation.allocator_digest import preserve
    sessions, problems = [], []
    for lf in sorted((run_alloc_dir / "transcripts").glob("launch-*.jsonl"),
                     key=lambda p: int(p.stem.split("-")[1])):
        text = lf.read_text(encoding="utf-8")
        spawns = len(re.findall(r'"type":"tool_use","id":"[^"]*","name":"Agent"', text))
        for sid in dict.fromkeys(re.findall(r'"session_id":"([0-9a-f-]{36})"', text)):
            found = sorted(p for p in projects.glob(f"*/{sid}") if (p / "subagents").is_dir())
            entry = {"launch": lf.name, "session_id": sid, "agent_spawns_in_launch": spawns,
                     "session_folders": [str(p) for p in found]}
            if len(found) > 1:
                problems.append(f"{sid}: session folder found {len(found)} times")
            elif not found and spawns:
                problems.append(f"{sid} ({lf.name}): {spawns} subagent spawns but no session folder")
            sessions.append(entry)
    dirs = [Path(e["session_folders"][0]) for e in sessions if len(e["session_folders"]) == 1]
    out = {"projects_root": str(projects), "sessions": sessions, "problems": problems, "preserved_files": 0,
           "hash_mismatches": []}
    if dirs and (run_alloc_dir / "transcripts" / "subagents").exists():
        problems.append("transcripts/subagents already in the copied run folder: not captured again")
    elif dirs:
        m = preserve(dirs, run_id, repo_results)
        out["preserved_files"] = len(m["files"])
        out["by_folder"] = {k: sum(1 for r in m["files"] if r.startswith(k + "/"))
                            for k in ("allocator", "checker", "unclassified")}
        out["hash_mismatches"] = m["hash_mismatches"]
    return out


def copy_back(clone_root: Path, run_id: str, repo_results: Path = ROOT / "results",
              data_root: Path | None = None, projects: Path | None = None) -> dict:
    from src.evaluation.run_report import build
    src_res = Path(clone_root) / "results"
    pairs = [(src_res / "allocations" / run_id, Path(repo_results) / "allocations" / run_id),
             (src_res / "evaluations" / run_id, Path(repo_results) / "evaluations" / run_id)]
    for s, d in pairs:
        if not s.is_dir():
            raise SystemExit(f"missing in the clone: {s}")
        if d.exists():
            raise SystemExit(f"{d} already exists: runs are never overwritten")
    hashes, mismatches = {}, []
    for s, d in pairs:
        before = _files(s)
        shutil.copytree(s, d)
        after = _files(d)
        key = d.parent.name
        hashes[key] = before
        mismatches += [f"{key}/{k}" for k in before if after.get(k) != before[k]]
        mismatches += [f"{key}/{k} (extra)" for k in after if k not in before]
    sub = capture_subagents(pairs[0][1], run_id, Path(repo_results), projects or projects_root())
    store = Store.from_run_dir(pairs[0][1])
    problems = check(store)
    report = build(run_id, Path(repo_results), data_root) if not mismatches else None
    out = {"run_id": run_id, "clone_root": str(Path(clone_root).resolve()),
           "copied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "files": hashes, "hash_mismatches": mismatches, "consistency_problems": problems,
           "run_report_rebuilt": report is not None, "subagent_transcripts": sub}
    (pairs[1][1] / "copy_back.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    o = copy_back(Path(sys.argv[1]), sys.argv[2])
    st = o["subagent_transcripts"]
    print(json.dumps({**{k: o[k] for k in ("run_id", "hash_mismatches", "consistency_problems",
                                           "run_report_rebuilt")},
                      "subagent_transcripts": {k: st.get(k) for k in ("preserved_files", "by_folder",
                                                                       "hash_mismatches", "problems")}}, indent=2))
    sys.exit(0 if not (o["hash_mismatches"] or o["consistency_problems"] or st["problems"]
                       or st["hash_mismatches"]) else 1)
