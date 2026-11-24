"""The Phase 2 analysis tables, ANALYSIS.md and HEADLINE_NUMBERS.csv (Decisions Log #128-#130)."""

from __future__ import annotations

import csv
import re
import subprocess
import sys

import pytest

from src.evaluation.analysis import ANALYSIS_DIR, SOURCES, TEMPLATE, fmt, lexicographic, load_numbers, render
from src.evaluation.checker_matching import match
from src.evaluation.dataset import ROOT


def test_analysis_md_and_headline_numbers_are_up_to_date():
    """ANALYSIS.md is exactly the template rendered with the committed tables, so no number in it is typed by
    hand; HEADLINE_NUMBERS.csv lists exactly the numbers it uses."""
    r = subprocess.run([sys.executable, "src/14_write_analysis.py", "--check"], cwd=ROOT, capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_headline_numbers_match_their_source_rows():
    numbers = load_numbers()
    rows = list(csv.DictReader(open(ANALYSIS_DIR / "HEADLINE_NUMBERS.csv", encoding="utf-8", newline="")))
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        src = numbers[r["id"]]
        assert (r["value"], r["source_file"], r["script"], r["pre_registered"]) == \
            (src["value"], src["source_file"], src["script"], src["pre_registered"]), r["id"]
        assert (ROOT / r["source_file"]).is_file() and (ROOT / r["script"]).is_file()


def test_every_table_cell_is_used_once_its_table_is_rendered():
    text, used = render(TEMPLATE.read_text(encoding="utf-8"), load_numbers())
    assert "{{" not in text
    ids = {u["id"] for u in used}
    tables = {i.split(".")[0] for i in ids}
    for r in load_numbers().values():
        if r["table"] in tables:
            assert r["id"] in ids, r["id"]


LABELS = re.compile(
    r"\{\{[^}]*\}\}|`[^`]*`|\]\([^)]*\)"                                   # tokens, code, link targets
    r"|^#+ [0-9.]+|§\s?\d+(?:\.\d+)?(?:[–-]#?\d+)?|#\d+(?:[–-]#?\d+)?|\d{4}-\d{2}-\d{2}"  # headings, §, #, dates
    r"|R\d-D\d+-\d+|\b(?i:items?|days?|day-|tiers?|tier-|levels?|Phase|steps?)\s?\d+(?:\.\d+)?"
    r"(?:\s?(?:and|–|-|,)\s?\d+(?:\.\d+)?)*"                                # item 4, items 3 and 7.3, tiers 3 and 2
    r"|\b[ABCFLRW]\d(?:[–-][ABCFLRW]?\d)?\b|\b(?:n|W) = \d\b|SV_[BN]|seed\d+|STRESS1|R52"
    r"|\bfloor of 0\b|\bscores 0 on A1\b", re.M)


def test_template_prose_has_no_hand_typed_number():
    """Every result in ANALYSIS.md comes through a {{n:id}} or {{table:..}} token (owner, 2026-11-24): outside
    the tokens the template may hold labels (sections, dates, days, tiers, run ids), never a number."""
    bare = [m.group(0) for m in re.finditer(r"\d+(?:[./]\d+)?", LABELS.sub(" ", TEMPLATE.read_text(encoding="utf-8")))]
    assert bare == []


def test_fmt_and_lexicographic():
    assert [fmt(x) for x in (0, 0.0, 1.05, 2 / 3, None, True, "4/5")] == ["0", "0", "1.05", "0.6667", "–", "yes", "4/5"]
    assert lexicographic((0, 0.15, 1.9), (0, 1.05, 1.2)) == "better"
    assert lexicographic((0, 1.05, 1.2), (0, 1.05, 1.2)) == "equal"
    assert lexicographic((0.1, 0, 0), (0, 9, 9)) == "worse"


def test_match_counts_leave_the_default_output_unchanged():
    audit = [{"day": 3, "type": "nurse_gap", "level": "Moderate"}, {"day": 3, "type": "nurse_gap", "level": "Major"},
             {"day": 4, "type": "beds_reversal", "level": "Minor"}]
    checker = [{"day": 3, "type": "nurse_gap", "severity": "Moderate"},
               {"day": 4, "type": "beds_reversal", "severity": "Moderate"},
               {"day": 5, "type": "beds_reversal", "severity": "Minor"}]
    plain, counted = match(audit, checker), match(audit, checker, counts=True)
    for k, v in plain.items():
        if k == "by_type":
            assert all(counted[k][t] == {**v[t], **{x: counted[k][t][x] for x in ("checker_matched", "level_same")}}
                       for t in v)
        elif k in ("by_level",):
            assert all({x: y for x, y in counted[k][lv].items() if x not in ("checker_matched", "level_same")} == v[lv]
                       for lv in v)
        elif k == "by_group":
            assert all({x: y for x, y in counted[k][g].items() if x not in ("checker_matched", "level_same")} == v[g]
                       for g in v)
        else:
            assert counted[k] == v, k
    assert counted["level_same"] == 0 and counted["matched"] == 2      # Major vs Moderate; Minor vs Moderate
    assert counted["by_level"]["Moderate"]["checker_matched"] == 2 and counted["by_level"]["Moderate"]["checker"] == 2


@pytest.mark.slow
def test_steps_10_to_13_reproduce_the_committed_tables(tmp_path):
    for script, name in (("src/10_main_comparison.py", "main_comparison.csv"),
                         ("src/11_checker_vs_audit.py", "checker_vs_audit.csv"),
                         ("src/12_checker_on_wrong_claims.py", "checker_on_wrong_claims.csv"),
                         ("src/13_stress1.py", "stress1.csv")):
        assert SOURCES[name] == script
        r = subprocess.run([sys.executable, script, "--out", str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (tmp_path / name).read_bytes() == (ANALYSIS_DIR / name).read_bytes(), name
