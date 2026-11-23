"""Run initialisation, in a development session (PROJECT_SPEC.md §3, Log #19).

    uv run python -m src.mcp_server.init_run --dataset seed20261107 [--run-id R1]

Creates the run directory, writes run_manifest.json, sets the state to READY and points ACTIVE_RUN at
the run. For frozen datasets the manifest check must pass first (CLAUDE.md §9.3). `--data-root` and
`--results-root` exist for the smoke test's synthetic fixture only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.evaluation.dataset import ROOT, load_dataset

from src.utils.paths import guard_write

from .store import POINTER, Store, now
from .workflow import code_version

RETRY_LIMIT = 3     # PROJECT_SPEC.md §10.3
RUN_SETTINGS = ROOT / ".claude" / "run-settings.json"


def configured_models() -> dict:
    """The model for all three roles, as set in the run settings (owner decision §11 #31)."""
    d = json.loads(RUN_SETTINGS.read_text(encoding="utf-8"))
    return {"main": d.get("model"), "subagents": d.get("env", {}).get("CLAUDE_CODE_SUBAGENT_MODEL")}


def init_run(dataset_id: str, run_id: str, data_root: Path = ROOT, results_root: Path = ROOT / "results",
             check_manifest: bool = True, set_pointer: bool = True, expose_violation_labels: bool = False,
             models: dict | None = None, replay_baseline: str | None = None) -> Store:
    if check_manifest:
        chk = subprocess.run([sys.executable, "-m", "src.data_generation.manifest", "--verify"], cwd=ROOT,
                             capture_output=True, text=True)
        if chk.returncode != 0:
            raise SystemExit(f"manifest check failed, no run initialised:\n{chk.stdout}{chk.stderr}")
    ds = load_dataset(dataset_id, root=Path(data_root))
    alloc_dir = guard_write(Path(results_root) / "allocations" / run_id)     # frozen run folders are read-only (R59)
    eval_dir = guard_write(Path(results_root) / "evaluations" / run_id)
    if alloc_dir.exists():
        raise SystemExit(f"{alloc_dir} already exists: runs are never overwritten")
    alloc_dir.mkdir(parents=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"run_id": run_id, "dataset_id": dataset_id, "data_root": str(Path(data_root).resolve()),
                "eval_dir": str(eval_dir.resolve()), "retry_limit": RETRY_LIMIT, "horizon": ds.horizon,
                "expose_violation_labels": bool(expose_violation_labels),
                "models": models or configured_models(),
                "code_version": code_version(), "started_at": now()}
    if replay_baseline:
        # Checker-only replay (owner decision §11 #42, Log #89): the baseline is recomputed here and its
        # allocations stored in the run directory; no agent tool reads this file.
        import tempfile
        from src.evaluation.runner import run_baseline
        with tempfile.TemporaryDirectory() as tmp:
            rd = run_baseline(replay_baseline, ds, Path(tmp))
            lines = [json.loads(x) for x in (rd / "allocation_state.jsonl").read_text(encoding="utf-8").splitlines()]
        days = {str(x["day"]): {"beds": x["beds"], "nurses": x["nurses"]} for x in lines
                if x["source"] == replay_baseline}
        (alloc_dir / "replay_allocations.json").write_text(json.dumps({"baseline": replay_baseline, "days": days},
                                                                      indent=2) + "\n", encoding="utf-8", newline="\n")
        manifest["checker_only_replay"] = replay_baseline
    (alloc_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    store = Store(alloc_dir, eval_dir)
    with store.lock():
        store.write_state({"run_id": run_id, "day": 0, "horizon": ds.horizon, "phase": "READY", "attempts": 0,
                           "accepted": False, "report_received": False})
    if set_pointer:
        POINTER.parent.mkdir(parents=True, exist_ok=True)
        POINTER.write_text(str(alloc_dir.resolve()) + "\n", encoding="utf-8", newline="\n")
    return store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--run-id")
    ap.add_argument("--data-root", default=str(ROOT))
    ap.add_argument("--results-root", default=str(ROOT / "results"))
    ap.add_argument("--skip-manifest-check", action="store_true", help="synthetic smoke fixture only")
    ap.add_argument("--replay-baseline", choices=["B0", "B1", "B2"],
                    help="checker-only run on a baseline's allocations (owner decision §11 #42)")
    ap.add_argument("--assisted", action="store_true",
                    help="optional 'assisted' ablation: violation labels in the what-if (owner decision §11 #29)")
    a = ap.parse_args()
    run_id = a.run_id or f"R-{a.dataset}-{now().replace(':', '').replace('-', '')}"
    store = init_run(a.dataset, run_id, Path(a.data_root), Path(a.results_root), not a.skip_manifest_check,
                     expose_violation_labels=a.assisted, replay_baseline=a.replay_baseline)
    print(f"initialised {run_id} at {store.alloc_dir}; ACTIVE_RUN updated")


if __name__ == "__main__":
    main()
