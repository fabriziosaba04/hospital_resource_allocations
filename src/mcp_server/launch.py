"""Launch (or resume) the active run in a headless run session. The same command for the dry run and R1–R3:

    uv run python -m src.mcp_server.launch

Starts `claude -p "Start." --agent dispatcher --settings .claude/run-settings.json` from the project root
(CLAUDE.md §9.1). The model comes from the run settings (owner decision §11 #31); it is also passed to the
subagents through CLAUDE_CODE_SUBAGENT_MODEL, so an environment variable in the user's shell cannot change
it. The transcript is streamed to <run>/transcripts/launch-<k>.jsonl line by line, so a killed launch keeps
what it had. After the session ends, the observed models are compared with run_manifest.json, the record
consistency check runs, and both go to <run>/launches.jsonl. Re-running the command resumes the run: the
dispatcher starts from get_workflow_status, and the server rebuilds every flag from the records.

The launcher refuses to start in a cloud-synced folder (OneDrive, Dropbox, Google Drive, iCloud; owner decision
§11 #44): R1-R3 and the stress run are launched from a clone outside it and copied back with
`python -m src.mcp_server.copy_back`. `--allow-synced-folder` is accepted for synthetic fixtures only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.dataset import ROOT

from .consistency import check
from .store import Store

PROMPT = "Start."
SYNCED_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud")


def synced_folder(path: Path) -> str | None:
    """The marker if `path` lies in a cloud-synced folder (owner decision §11 #44, Log #90): a path part
    containing OneDrive, Dropbox, Google Drive or iCloud, or a path under an OneDrive environment root."""
    p = str(Path(path).resolve())
    low = p.lower()
    for mk in SYNCED_MARKERS:
        if any(mk in part.lower() for part in Path(p).parts):
            return mk
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(var)
        if root and low.startswith(str(Path(root).resolve()).lower()):
            return var
    return None


DATA_MANIFEST = ROOT / "data" / "MANIFEST.json"


def frozen_dataset(dataset_id: str) -> bool:
    """True for a dataset listed in the frozen-data manifest (data-v1.0)."""
    if not DATA_MANIFEST.exists():
        return True                      # cannot tell: treat as frozen, so the guard stays strict
    return f'"{dataset_id}' in DATA_MANIFEST.read_text(encoding="utf-8") or f"/{dataset_id}/" in         DATA_MANIFEST.read_text(encoding="utf-8")


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


def guard(store: Store, allow_synced: bool = False) -> str | None:
    """Refuse a run in a synced folder. `allow_synced` is accepted only for synthetic fixtures (dry runs),
    never for a frozen dataset. Returns the marker when a synthetic run is allowed in a synced folder."""
    m = store.manifest()
    mk = synced_folder(ROOT) or synced_folder(store.alloc_dir)
    if mk is None:
        return None
    if allow_synced and not frozen_dataset(m["dataset_id"]):
        return mk
    raise SystemExit(f"refusing to launch: the project is in a synced folder ({mk}: {ROOT}). Run from a clone "
                     "outside OneDrive or any synced folder (PROJECT_SPEC.md Log #90)."
                     + ("" if not allow_synced else " --allow-synced-folder is for synthetic fixtures only."))


def launch(store: Store, max_turns: int = 2000, synced: str | None = None) -> dict:
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
           "synced_folder": synced, "state_after": store.read_state(), "consistency_problems": check(store),
           "stderr_tail": stderr[-1500:]}
    with open(store.alloc_dir / "launches.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main() -> int:
    store = Store.active()
    synced = guard(store, allow_synced="--allow-synced-folder" in sys.argv[1:])
    rec = launch(store, synced=synced)
    print(json.dumps({k: rec[k] for k in ("launch", "exit_code", "duration_s", "models_match",
                                          "consistency_problems")}, indent=2))
    print("state:", rec["state_after"]["phase"], "day", rec["state_after"]["day"])
    return 0 if rec["exit_code"] == 0 and not rec["consistency_problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
