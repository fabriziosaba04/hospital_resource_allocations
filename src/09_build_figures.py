"""Step 9: the static figures F1-F6 of ANALYSIS.md (figure plan, owner decision §11 #49; Decisions Log #136).

    uv run python src/09_build_figures.py [--out DIR]      # default: results/figures/

This script is the one script that makes each of F1-F6 (`src/evaluation/report_figures.py`):

  F1_overflow_by_tier.png        A3 raw, tiers 3 and 2, with the floor        <- results/analysis/main_comparison.csv
  F2_nurse_gap_by_tier.png       A2 SV_N per tier, with the floor              <- results/analysis/main_comparison.csv
  F3_beds_over_time.png          beds per department and day, against census  <- the committed run records
  F4_nurses_vs_requirement.png   nurses per department and day, against N1    <- the committed run records
  F5_fairness_dispersion.png     B1 overflow-rate dispersion per level         <- results/analysis/main_comparison.csv
  F6_checker_vs_audit.png        CHECKER against the audit, R1-R3 and STRESS1  <- checker_vs_audit.csv, stress1.csv

Run it after steps 10-13, which write the tables it reads. F1, F2 and F5 have a second panel without B0 on its
own scale, so the small differences between the runs and B1/B2 stay visible. The figures show recorded
decisions only and invent no movements.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import load_numbers  # noqa: E402
from src.evaluation.figures import check_frame  # noqa: E402
from src.evaluation.report_figures import FIG_DIR, _frames, fig1, fig2, fig3, fig4, fig5, fig6  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(FIG_DIR))
    out = Path(ap.parse_args().out)
    numbers = load_numbers()
    ds, frames = _frames()
    problems = {p: check_frame(rows, ds.max_beds) for p, rows in frames.items()}
    if any(problems.values()):
        print("record-field problems:", {p: v for p, v in problems.items() if v})
        sys.exit(1)
    for f in (lambda: fig1(numbers, out), lambda: fig2(numbers, out), lambda: fig3(frames, ds.max_beds, out),
              lambda: fig4(frames, out), lambda: fig5(numbers, out), lambda: fig6(numbers, out)):
        f()
    for p in sorted(out.glob("F*.png")):
        print(f"{p.name}: {p.stat().st_size // 1024} KB")
