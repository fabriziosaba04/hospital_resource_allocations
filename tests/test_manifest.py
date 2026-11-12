"""The frozen data (tag data-v1.0) must match data/MANIFEST.json, and must be reproducible."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.data_generation.manifest import verify

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "MANIFEST.json").exists(), reason="data not frozen yet")


@pytest.mark.slow
def test_frozen_data_match_manifest_and_regenerate_exactly():
    assert verify(ROOT, regenerate=True) == []


def test_manifest_detects_tampering(tmp_path):
    for sub in ("data", "src/data_generation/configs"):
        shutil.copytree(ROOT / sub, tmp_path / sub)
    for f in json.loads((ROOT / "data" / "MANIFEST.json").read_text(encoding="utf-8"))["generator_code"]:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, tmp_path / f)
    assert verify(tmp_path) == []
    target = tmp_path / "data" / "raw" / "seed20261107" / "patient_registry.csv"
    target.write_bytes(target.read_bytes().replace(b"P000001,", b"P000001 ,", 1))
    (tmp_path / "data" / "raw" / "seed20261107" / "extra.csv").write_text("x\n")
    problems = verify(tmp_path)
    assert any("hash mismatch" in p and "patient_registry" in p for p in problems)
    assert any("unlisted data file" in p and "extra.csv" in p for p in problems)
