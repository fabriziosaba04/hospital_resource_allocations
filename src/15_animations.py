"""Step 15: one animation per agent run, net balance per department (owner decision §11 #51; Log #137).

    uv run python src/15_animations.py [RUN ...] [--out DIR]      # default: R1 R2 R3 -> results/figures/animations/

30 frames, one per day. Per frame: for each department, its beds and its nurses in effect minus the common
initial allocation of day 1 (the reference §11 #51 and EVALUATION_PLAN.md §10 leave open), in two panels, with
the day counter and that day's pools. No arrows between departments: the records hold allocations, not
transfers. The y-limits are computed over R1-R3 together, so the three GIFs share them whatever runs are asked
for. GIF through matplotlib's Pillow writer (no ffmpeg).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.analysis import AGENT_RUNS, PRIMARY  # noqa: E402
from src.evaluation.dataset import load_dataset  # noqa: E402
from src.evaluation.report_figures import FIG_DIR, animate, common_limits  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", default=AGENT_RUNS)
    ap.add_argument("--out", default=str(FIG_DIR / "animations"))
    a = ap.parse_args()
    ds = load_dataset(PRIMARY)
    pools = {"beds": ds.pool_beds, "nurses": ds.pool_nurses}
    limits = common_limits()
    for run in a.runs:
        p = animate(run, limits, Path(a.out), pools)
        print(f"{p.name}: {p.stat().st_size // 1024} KB (limits beds ±{limits['beds']}, nurses ±{limits['nurses']})")
