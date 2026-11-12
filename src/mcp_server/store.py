"""Record store (PROJECT_SPEC.md §3–§4): append-only JSON Lines, an atomically replaced state.json,
and a lock file around every write. Every call re-reads from disk; nothing is cached (Log #9)."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.dataset import ROOT

POINTER = ROOT / "results" / "allocations" / "ACTIVE_RUN"

# record name -> (directory key, file name)
RECORDS = {
    "observed_state": ("alloc", "observed_state.jsonl"),
    "allocation_state": ("alloc", "allocation_state.jsonl"),
    "decision_history": ("alloc", "decision_history.jsonl"),
    "bed_assignment_state": ("alloc", "bed_assignment_state.jsonl"),
    "workflow": ("alloc", "workflow.jsonl"),
    "deterministic_audit": ("eval", "deterministic_audit.jsonl"),
    "validation_history": ("eval", "validation_history.jsonl"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StoreError(RuntimeError):
    pass


class Store:
    def __init__(self, alloc_dir: Path, eval_dir: Path):
        self.alloc_dir, self.eval_dir = Path(alloc_dir), Path(eval_dir)

    @classmethod
    def active(cls) -> "Store":
        if not POINTER.exists():
            raise StoreError("no active run: initialise one with python -m src.mcp_server.init_run")
        alloc_dir = Path(POINTER.read_text(encoding="utf-8").strip())
        if not alloc_dir.is_absolute():
            alloc_dir = ROOT / alloc_dir
        manifest = json.loads((alloc_dir / "run_manifest.json").read_text(encoding="utf-8"))
        return cls(alloc_dir, Path(manifest["eval_dir"]))

    # ------------------------------------------------------------------ files
    def path(self, record: str) -> Path:
        key, name = RECORDS[record]
        return (self.alloc_dir if key == "alloc" else self.eval_dir) / name

    def manifest(self) -> dict:
        return json.loads((self.alloc_dir / "run_manifest.json").read_text(encoding="utf-8"))

    def read(self, record: str) -> list[dict]:
        p = self.path(record)
        if not p.exists():
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def read_state(self) -> dict:
        return json.loads((self.alloc_dir / "state.json").read_text(encoding="utf-8"))

    @contextmanager
    def lock(self, timeout: float = 30.0):
        lock = self.alloc_dir / ".lock"
        start = time.monotonic()
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                if time.monotonic() - start > timeout:
                    raise StoreError(f"lock {lock} held for more than {timeout}s")
                time.sleep(0.05)
        try:
            os.write(fd, str(os.getpid()).encode())
            yield
        finally:
            os.close(fd)
            lock.unlink(missing_ok=True)

    # ------------------------------------------------------------------ writes (call inside lock())
    def write_state(self, state: dict) -> None:
        tmp = self.alloc_dir / "state.json.tmp"
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.replace(tmp, self.alloc_dir / "state.json")

    def append(self, record: str, line: dict) -> dict:
        p = self.path(record)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return line
