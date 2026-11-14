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
  4. writes `results/evaluations/<run>/copy_back.json` with the hashes and the outcome.
It refuses to overwrite an existing run folder, and refuses a clone inside a synced folder only as a source
warning (the copy itself is harmless).
"""

from __future__ import annotations

import hashlib
import json
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


def copy_back(clone_root: Path, run_id: str, repo_results: Path = ROOT / "results",
              data_root: Path | None = None) -> dict:
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
    store = Store.from_run_dir(pairs[0][1])
    problems = check(store)
    report = build(run_id, Path(repo_results), data_root) if not mismatches else None
    out = {"run_id": run_id, "clone_root": str(Path(clone_root).resolve()),
           "copied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "files": hashes, "hash_mismatches": mismatches, "consistency_problems": problems,
           "run_report_rebuilt": report is not None}
    (pairs[1][1] / "copy_back.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    o = copy_back(Path(sys.argv[1]), sys.argv[2])
    print(json.dumps({k: o[k] for k in ("run_id", "hash_mismatches", "consistency_problems",
                                        "run_report_rebuilt")}, indent=2))
    sys.exit(0 if not o["hash_mismatches"] and not o["consistency_problems"] else 1)
