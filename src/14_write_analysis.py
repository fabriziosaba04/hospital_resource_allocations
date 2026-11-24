"""Step 14: write ANALYSIS.md and results/analysis/HEADLINE_NUMBERS.csv (Decisions Log #128).

    uv run python src/14_write_analysis.py [--check]

Renders src/evaluation/analysis_template.md with the tables written by steps 10-13 (`analysis.render`): every
number in ANALYSIS.md is a cell of one of those tables, so none is typed by hand. HEADLINE_NUMBERS.csv lists each
number used, with its source file and script. `--check` writes nothing and exits 1 if either file is out of date
(also run by tests/test_analysis.py).
"""
import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import ANALYSIS_DIR, NUMBER_COLUMNS, TEMPLATE, load_numbers, render  # noqa: E402
from src.utils.paths import guard_write  # noqa: E402


def expected() -> tuple[str, str]:
    text, rows = render(TEMPLATE.read_text(encoding="utf-8"), load_numbers())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=NUMBER_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return text, buf.getvalue()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text, csv_text = expected()
    md, nums = ROOT / "ANALYSIS.md", ANALYSIS_DIR / "HEADLINE_NUMBERS.csv"
    if a.check:
        ok = md.exists() and md.read_text(encoding="utf-8") == text and nums.exists() \
            and nums.read_text(encoding="utf-8") == csv_text
        print("ANALYSIS.md and HEADLINE_NUMBERS.csv are", "up to date" if ok else "OUT OF DATE")
        sys.exit(0 if ok else 1)
    guard_write(md).write_text(text, encoding="utf-8", newline="\n")       # frozen run folders are read-only (R59)
    guard_write(nums).write_text(csv_text, encoding="utf-8", newline="\n")
    print(f"wrote ANALYSIS.md and {nums.relative_to(ROOT)} ({csv_text.count(chr(10)) - 1} numbers)")
