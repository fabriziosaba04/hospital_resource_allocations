"""Comparisons used by the numbered entry scripts (src/01_... to src/09_...): a recomputed file against the
committed one. Read-only; nothing here writes."""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.paths import long_path

VOLATILE = ("created_at",)          # timestamps written at recomputation time; everything else must be equal


def _strip(x, keys):
    if isinstance(x, dict):
        return {k: _strip(v, keys) for k, v in x.items() if k not in keys}
    if isinstance(x, list):
        return [_strip(v, keys) for v in x]
    return x


def _load(p: Path):
    text = long_path(p).read_text(encoding="utf-8")
    if p.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def same(recomputed: Path, committed: Path, ignore: tuple[str, ...] = VOLATILE) -> bool:
    """JSON / JSONL compared as data with the `ignore` keys removed; any other file compared byte for byte."""
    if recomputed.suffix in (".json", ".jsonl"):
        return _strip(_load(recomputed), ignore) == _strip(_load(committed), ignore)
    return long_path(recomputed).read_bytes() == long_path(committed).read_bytes()


def report(rows: list[tuple[str, Path, Path]]) -> int:
    """Print one line per (label, recomputed, committed); return 0 if all are equal, 1 otherwise."""
    bad = 0
    for label, new, old in rows:
        if not long_path(old).exists():
            print(f"  {label}: no committed file to compare ({old.name})")
            continue
        ok = same(new, old)
        bad += not ok
        print(f"  {label}: {'EQUAL' if ok else 'DIFFERENT'} to the committed {old.name}")
    print("RESULT:", "OK" if not bad else f"{bad} DIFFERENT")
    return 1 if bad else 0
