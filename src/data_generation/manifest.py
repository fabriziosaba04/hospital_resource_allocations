"""Data freeze manifest (data/MANIFEST.json) and its verification.

    uv run python -m src.data_generation.manifest --write          # at freeze time (needs a git commit)
    uv run python -m src.data_generation.manifest --verify         # hashes, completeness, generator code
    uv run python -m src.data_generation.manifest --verify --regenerate   # also rebuild every dataset

The manifest lists the SHA-256 of every frozen data file and template config, the SHA-256 of the
generator code (line endings normalised to LF) and the git commit of the generator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DATASETS = ["seed20261107", "seed20261108", "seed20261109", "seed20261107_stress"]
CODE_FILES = [
    "src/data_generation/generator.py",
    "src/data_generation/los.py",
    "src/data_generation/__main__.py",
    "src/data_generation/validation.py",
    "src/utils/constants.py",
]
CONFIG_GLOB = "src/data_generation/configs/*.json"
TAG = "data-v1.0"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path, normalise_eol: bool = False) -> str:
    b = path.read_bytes()
    if normalise_eol:
        b = b.replace(b"\r\n", b"\n")
    return sha256_bytes(b)


def dataset_files(root: Path, dataset_id: str) -> list[Path]:
    return sorted([*(root / "data" / "raw" / dataset_id).glob("*"), *(root / "data" / "metadata" / dataset_id).glob("*")])


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def git_commit(root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def build(root: Path, commit: str) -> dict:
    datasets = {}
    for ds in DATASETS:
        files = dataset_files(root, ds)
        if not files:
            raise FileNotFoundError(f"dataset {ds} has no files")
        report = json.loads((root / "data" / "processed" / ds / "validation_report.json").read_text(encoding="utf-8"))
        if not report["accepted"]:
            raise RuntimeError(f"dataset {ds} was rejected by validation; it cannot be frozen")
        datasets[ds] = {
            "validation": f"{report['n_passed']}/{report['n_checks']} checks passed",
            "files": {rel(root, f): sha256_file(f) for f in files},
        }
    return {
        "tag": TAG,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator_commit": commit,
        "hash": "sha256 of the file bytes; code files hashed with CRLF normalised to LF",
        "datasets": datasets,
        "template_configs": {rel(root, f): sha256_file(f) for f in sorted(root.glob(CONFIG_GLOB))},
        "generator_code": {f: sha256_file(root / f, normalise_eol=True) for f in CODE_FILES},
    }


def verify(root: Path, regenerate: bool = False) -> list[str]:
    """Return a list of problems; an empty list means the frozen data are intact."""
    path = root / "data" / "MANIFEST.json"
    if not path.exists():
        return ["data/MANIFEST.json is missing"]
    m = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    listed = set()
    for ds, entry in m["datasets"].items():
        for f, h in entry["files"].items():
            listed.add(f)
            p = root / f
            if not p.exists():
                problems.append(f"missing: {f}")
            elif sha256_file(p) != h:
                problems.append(f"hash mismatch: {f}")
    for sub in ("raw", "metadata"):
        for p in sorted((root / "data" / sub).rglob("*")):
            if p.is_file() and rel(root, p) not in listed:
                problems.append(f"unlisted data file: {rel(root, p)}")
    for f, h in m["template_configs"].items():
        if not (root / f).exists() or sha256_file(root / f) != h:
            problems.append(f"template config changed or missing: {f}")
    for p in sorted(root.glob(CONFIG_GLOB)):
        if rel(root, p) not in m["template_configs"]:
            problems.append(f"unlisted template config: {rel(root, p)}")
    for f, h in m["generator_code"].items():
        if not (root / f).exists() or sha256_file(root / f, normalise_eol=True) != h:
            problems.append(f"generator code changed since the freeze: {f}")
    if regenerate:
        problems += _regenerate(root, m)
    return problems


def _regenerate(root: Path, m: dict) -> list[str]:
    """Rebuild every dataset from its frozen configs and compare the bytes."""
    from .generator import generate, write_dataset

    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for ds, entry in m["datasets"].items():
            gen = json.loads((root / "data" / "metadata" / ds / "generation_config.json").read_text(encoding="utf-8"))
            env = json.loads((root / "data" / "metadata" / ds / "environment_config.json").read_text(encoding="utf-8"))
            write_dataset(generate(gen, env, int(gen["seed"]), dataset_id=ds), tmp)
            for f, h in entry["files"].items():
                q = tmp / f
                if not q.exists() or sha256_file(q) != h:
                    problems.append(f"regeneration differs: {f}")
    return problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--verify", action="store_true")
    p.add_argument("--regenerate", action="store_true")
    p.add_argument("--root", default=".")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    if args.write:
        m = build(root, git_commit(root))
        (root / "data" / "MANIFEST.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8", newline="\n")
        n = sum(len(e["files"]) for e in m["datasets"].values())
        print(f"wrote data/MANIFEST.json: {n} data files, {len(m['template_configs'])} template configs, "
              f"generator commit {m['generator_commit']}")
        return 0
    problems = verify(root, regenerate=args.regenerate)
    for pr in problems:
        print("FAIL", pr)
    print("manifest OK" if not problems else f"manifest FAILED ({len(problems)} problem(s))")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
