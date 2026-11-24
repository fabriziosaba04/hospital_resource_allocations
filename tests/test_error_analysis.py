"""ERROR_ANALYSIS.md, its tables, its number list and its register (Decisions Log #138)."""

from __future__ import annotations

import csv
import re
import subprocess
import sys

from src.evaluation.analysis import ANALYSIS_DIR, load_numbers, read_table, typed_numbers
from src.evaluation.dataset import ROOT

TEMPLATE = ROOT / "src" / "evaluation" / "error_analysis_template.md"


def test_error_analysis_is_up_to_date():
    r = subprocess.run([sys.executable, "src/16_error_analysis.py", "--check"], cwd=ROOT, capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_template_prose_has_no_hand_typed_number():
    assert typed_numbers(TEMPLATE.read_text(encoding="utf-8")) == []


def test_numbers_match_their_sources():
    numbers = load_numbers()
    numbers.update({r["id"]: {**r, "source_file": "results/analysis/error_analysis.csv"}
                    for r in read_table(ANALYSIS_DIR / "error_analysis.csv")})
    rows = list(csv.DictReader(open(ANALYSIS_DIR / "ERROR_NUMBERS.csv", encoding="utf-8", newline="")))
    assert len({r["id"] for r in rows}) == len(rows) > 0
    for r in rows:
        assert (r["value"], r["source_file"]) == (numbers[r["id"]]["value"], numbers[r["id"]]["source_file"]), r["id"]


def test_register_cites_real_log_entries():
    log = (ROOT / "docs" / "REFLECTION_LOG.md").read_text(encoding="utf-8")
    entries = {int(n) for n in re.findall(r"^### R(\d+)\.", log, re.M)}
    reg = read_table(ANALYSIS_DIR / "error_register.csv")
    assert len({r["id"] for r in reg}) == len(reg)
    for r in reg:
        assert all(r[k].strip() for k in ("what", "where", "how_found", "found_by", "consequence", "fix")), r["id"]
        m = re.fullmatch(r"R(\d+)-R(\d+)", r["id"])
        ids = range(int(m.group(1)), int(m.group(2)) + 1) if m else [int(n) for n in re.findall(r"R(\d+)", r["id"])]
        assert all(i in entries for i in ids), r["id"]
    b = {int(n) for r in reg if r["part"] == "B" for n in re.findall(r"R(\d+)", r["id"])}
    assert not b & {4, 6, 15, 32, 33, 52}                 # excluded with a stated reason in ERROR_ANALYSIS.md


def test_links_to_analysis_sections_resolve():
    slug = lambda h: re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")  # noqa: E731 (GitHub anchors)
    heads = {slug(l.lstrip("#")) for l in (ROOT / "ANALYSIS.md").read_text(encoding="utf-8").splitlines()
             if l.startswith("#")}
    used = set(re.findall(r"ANALYSIS\.md#([^)]+)", (ROOT / "ERROR_ANALYSIS.md").read_text(encoding="utf-8")))
    assert used and used <= heads, used - heads
