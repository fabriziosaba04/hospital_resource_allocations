"""Long-path-safe file access on Windows (Decisions Log #116, R56).

The repository sits deep inside OneDrive (132 characters), and Windows without `LongPathsEnabled` rejects any
path of 260 characters or more (MAX_PATH counts the terminating NUL). R2's spilled tool results land at exactly
260. `long_path` returns the extended-length form (`\\\\?\\C:\\...`), which the Win32 file API accepts up to about
32,767 characters; on other systems it returns the path unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path


def long_path(p) -> Path:
    if os.name != "nt":
        return Path(p)
    s = os.path.abspath(str(p)).replace("/", "\\")          # abspath collapses "..", which the extended form does not
    if s.startswith("\\\\?\\"):
        return Path(s)
    return Path("\\\\?\\UNC\\" + s[2:] if s.startswith("\\\\") else "\\\\?\\" + s)


def walk_files(root) -> dict[str, Path]:
    """Every file under `root`, keyed by its '/'-separated path relative to `root`, opened via `long_path`."""
    base = long_path(root)
    out = {}
    for dirpath, _, names in os.walk(base):
        for n in names:
            p = Path(dirpath) / n
            out[str(p.relative_to(base)).replace("\\", "/")] = p
    return dict(sorted(out.items()))


# --- Frozen run folders (owner decision 2026-11-23, R59, R60) -------------------------------------------------
# A run whose `results/evaluations/<run>/copy_back.json` exists is frozen evidence: nothing may write into
# `results/allocations/<run>/` or `results/evaluations/<run>/` any more. Every writer in src/ calls `guard_write`
# before writing; the only writers that do not are copy-back itself (`src/mcp_server/copy_back.py` and
# `allocator_digest.preserve`), which run before `copy_back.json` exists and refuse a folder already in place.
# Recomputations default to `results/analysis/recomputed/<run_id>/` (`recomputed_dir`).

RESULTS_ROOT = Path(__file__).resolve().parents[2] / "results"     # the repository's results; tests patch it


class FrozenRunError(RuntimeError):
    """A write was attempted into the run folder of a copied-back (frozen) run."""


_EXT, _EXT_UNC = "\\\\?\\", "\\\\?\\UNC\\"          # the extended-length prefixes added by long_path


def _norm(p) -> str:
    """Plain, absolute, case-folded form of a path, with any extended-length prefix removed."""
    s = str(p)
    if s.startswith(_EXT_UNC):
        s = "\\\\" + s[len(_EXT_UNC):]
    elif s.startswith(_EXT):
        s = s[len(_EXT):]
    return os.path.abspath(s).replace("\\", "/").lower()


def frozen_run_of(path) -> str | None:
    """The run id if `path` lies inside the run folder of a frozen run under RESULTS_ROOT, else None."""
    root, p = _norm(RESULTS_ROOT), _norm(path)
    if not p.startswith(root + "/"):
        return None
    parts = p[len(root) + 1:].split("/")
    if len(parts) < 2 or parts[0] not in ("allocations", "evaluations") or not parts[1]:
        return None
    ev = long_path(Path(RESULTS_ROOT) / "evaluations")
    names = {n.lower(): n for n in os.listdir(ev)} if ev.is_dir() else {}
    run = names.get(parts[1])
    if run is not None and (ev / run / "copy_back.json").is_file():
        return run
    return None


def guard_write(path):
    """Raise FrozenRunError if `path` is inside a frozen run folder; otherwise return `path` unchanged."""
    run = frozen_run_of(path)
    if run is not None:
        raise FrozenRunError(f"refused: {path} is inside the frozen run folder of {run} (copy_back.json exists). "
                             f"Write recomputations to {recomputed_dir(run)} instead.")
    return path


def recomputed_dir(run_id: str, results_root=None) -> Path:
    """Default output folder for anything recomputed from a run's records."""
    return Path(results_root if results_root is not None else RESULTS_ROOT) / "analysis" / "recomputed" / run_id
