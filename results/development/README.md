# Development material

The runs and fixtures used to build and test the system before the evaluation runs, all on **synthetic fixtures**, never on the frozen data. They were moved here from results/allocations, results/evaluations, results/dry_runs and results/visualizations in the clean-up of 2026-11-23 (`docs/CLEANUP_PLAN.md`). Their content is unchanged.

| Folder | What it is |
| --- | --- |
| `allocations/DRY1-SMOKE5/`, `evaluations/DRY1-SMOKE5/` | First dry run, 5-day SMOKE5 fixture (2026-11-12) |
| `allocations/DRY2-HARD10/`, `evaluations/DRY2-HARD10/` | Dry run on the hard 10-day HARD10 fixture (2026-11-14), the source of the claim-verification test case |
| `allocations/DRY3-RESUME/`, `evaluations/DRY3-RESUME/` | Resume test from the clone across three launches (2026-11-15) |
| `allocations/CHK-B2-HARD10/`, `evaluations/CHK-B2-HARD10/` | CHECKER-only replay of baseline B2 on HARD10 (owner decision §11 #42) |
| `allocations/B?-HARD10/`, `evaluations/B?-HARD10/` | Baselines on HARD10 |
| `dry_runs/SMOKE5_fixture/`, `dry_runs/HARD10_fixture/` | The two synthetic fixtures (data in the same layout as `data/`) |
| `figures/HARD10/` | Figures built on HARD10 while developing the figure code |

**The two `make_*_claims.py` scripts** in `evaluations/DRY2-HARD10/` (`make_day7_claims.py`, `make_full_claims.py`) are the hand-written claim encodings that produced DRY2's `explanation_claims_day7_spec.json` and `explanation_claims_full_spec.json`. They stay next to their outputs for provenance and resolve their paths relative to their own folder. Nothing imports them.

The run manifests in these folders record the absolute paths where the runs were made. They are historical and never used to locate files. `resolve_data_root` in `src/evaluation/run_report.py` maps an old results/dry_runs/<fixture> path to `dry_runs/<fixture>` here.
