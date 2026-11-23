"""Step 2 (optional, slow): Monte Carlo reference ranges of the generator, seeds 1..n (Decisions Log #30, #33).

    uv run python src/02_montecarlo.py [--n 1000]

Thin wrapper around `src.data_generation.montecarlo` and `src.data_generation.mc_analysis`. Both write under
`<root>/data/processed/montecarlo/`, so they run with a separate root, results/analysis/recomputed/montecarlo/,
holding a copy of the primary dataset; the committed data/ is never written. The summary is then compared with
the committed data/processed/montecarlo/montecarlo_summary.json.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_generation import mc_analysis, montecarlo  # noqa: E402
from src.utils.compare import report  # noqa: E402
from src.utils.paths import guard_write  # noqa: E402

PRIMARY = "seed20261107"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    n = ap.parse_args().n
    root = guard_write(ROOT / "results" / "analysis" / "recomputed" / "montecarlo")
    for sub in ("raw", "metadata"):
        shutil.copytree(ROOT / "data" / sub / PRIMARY, root / "data" / sub / PRIMARY, dirs_exist_ok=True)
    montecarlo.main(["--n", str(n), "--compare", PRIMARY, "--root", str(root)])
    mc_analysis.main(["--n", str(n), "--primary", PRIMARY, "--root", str(root)])
    name = "montecarlo_summary.json"
    sys.exit(report([(f"Monte Carlo summary (n={n})", root / "data/processed/montecarlo" / name,
                      ROOT / "data/processed/montecarlo" / name)]))
