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
