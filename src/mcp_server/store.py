"""Record store (PROJECT_SPEC.md §3–§4): append-only JSON Lines, an atomically replaced state.json,
and a lock file around every write. Every call re-reads from disk; nothing is cached (Log #9).

Robustness (owner decision §11 #33, Log #79):
  - stale locks: the lock file records pid and time; a lock older than STALE_LOCK_SECONDS is broken and
    the break is logged in `lock_breaks.jsonl`;
  - `os.replace` is retried briefly (a synced folder can hold a file for a moment);
  - a crash hook for the resume tests: `HRA_CRASH_AFTER=<record>:<n>` makes the process exit abruptly
    right after its n-th append to <record>. Unset in real runs.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.evaluation.dataset import ROOT

POINTER = ROOT / "results" / "allocations" / "ACTIVE_RUN"
STALE_LOCK_SECONDS = 120.0      # every locked operation takes well under a second on the 30-day data

# record name -> (directory key, file name)
RECORDS = {
    "observed_state": ("alloc", "observed_state.jsonl"),
    "allocation_state": ("alloc", "allocation_state.jsonl"),
    "decision_history": ("alloc", "decision_history.jsonl"),
    "bed_assignment_state": ("alloc", "bed_assignment_state.jsonl"),
    "workflow": ("alloc", "workflow.jsonl"),
    "deterministic_audit": ("eval", "deterministic_audit.jsonl"),
    "validation_history": ("eval", "validation_history.jsonl"),
    "process_calls": ("eval", "process_calls.jsonl"),    # what-if/validate calls; no agent tool reads it
}

_append_counts: dict[str, int] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StoreError(RuntimeError):
    pass


def pid_alive(pid: int) -> bool:
    """True if a process with this id exists. On Windows, uses OpenProcess (os.kill(pid, 0) would kill it)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259                                  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _crash_hook(record: str) -> None:
    spec = os.environ.get("HRA_CRASH_AFTER")
    if not spec:
        return
    name, n = spec.rsplit(":", 1)
    if name == record:
        _append_counts[record] = _append_counts.get(record, 0) + 1
        if _append_counts[record] == int(n):
            os._exit(17)            # abrupt: no cleanup, no lock release, like a killed process


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

    @classmethod
    def from_run_dir(cls, alloc_dir: Path) -> "Store":
        """Paths resolved relative to the run directory, <results>/allocations/<run> and
        <results>/evaluations/<run>, never from the manifest's absolute `eval_dir`, so a run folder copied
        from a clone is read in place (owner decision §11 #44, Log #90)."""
        alloc_dir = Path(alloc_dir).resolve()
        return cls(alloc_dir, alloc_dir.parent.parent / "evaluations" / alloc_dir.name)

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
        out = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # a torn final line from a process killed mid-write; complete lines are kept
                    continue
        return out

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
                self._break_if_stale(lock)
                if time.monotonic() - start > timeout:
                    raise StoreError(f"lock {lock} held for more than {timeout}s")
                time.sleep(0.05)
        try:
            os.write(fd, json.dumps({"pid": os.getpid(), "t": time.time()}).encode())
            os.close(fd)
            yield
        finally:
            lock.unlink(missing_ok=True)

    def _break_if_stale(self, lock: Path) -> None:
        try:
            info = json.loads(lock.read_text(encoding="utf-8") or "{}")
            age = time.time() - float(info.get("t", lock.stat().st_mtime))
        except (OSError, ValueError):
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                return
            info = {}
        holder_dead = "pid" in info and not pid_alive(int(info["pid"]))
        if holder_dead or age > STALE_LOCK_SECONDS:
            lock.unlink(missing_ok=True)
            with open(self.alloc_dir / "lock_breaks.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({"at": now(), "age_s": round(age, 1), "holder": info,
                                    "reason": "holder process gone" if holder_dead else "older than limit"}) + "\n")

    # ------------------------------------------------------------------ writes (call inside lock())
    def write_state(self, state: dict) -> None:
        tmp = self.alloc_dir / "state.json.tmp"
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        for i in range(10):
            try:
                os.replace(tmp, self.alloc_dir / "state.json")
                return
            except PermissionError:
                if i == 9:
                    raise
                time.sleep(0.2)

    def append(self, record: str, line: dict) -> dict:
        p = self.path(record)
        p.parent.mkdir(parents=True, exist_ok=True)
        torn = False
        if p.exists() and p.stat().st_size > 0:
            with open(p, "rb") as f:
                f.seek(-1, os.SEEK_END)
                torn = f.read(1) != b"\n"
        with open(p, "a", encoding="utf-8", newline="\n") as f:
            if torn:
                f.write("\n")          # never glue a new record onto a line cut off by a kill
            f.write(json.dumps(line, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        _crash_hook(record)
        return line
