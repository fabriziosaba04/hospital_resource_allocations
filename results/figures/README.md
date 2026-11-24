# Figures

Made by the numbered scripts and embedded in [`ANALYSIS.md`](../../ANALYSIS.md). Colours: one fixed colour per policy (`src/evaluation/figure_style.py`). PNG at 200 dpi.

| File | Made by | Content | Reads |
| --- | --- | --- | --- |
| [`F1_overflow_by_tier.png`](F1_overflow_by_tier.png) | `src/09_build_figures.py` | A3 raw overflow, tiers 3 and 2, with the floor; zoom panel without B0 | `results/analysis/main_comparison.csv` |
| [`F2_nurse_gap_by_tier.png`](F2_nurse_gap_by_tier.png) | `src/09_build_figures.py` | A2 SV_N per tier, with the floor; zoom panel without B0 | `results/analysis/main_comparison.csv` |
| [`F3_beds_over_time.png`](F3_beds_over_time.png) | `src/09_build_figures.py` | beds per department and day, against census and the cap | the committed run records |
| [`F4_nurses_vs_requirement.png`](F4_nurses_vs_requirement.png) | `src/09_build_figures.py` | nurses per department and day, against the N1 requirement | the committed run records |
| [`F5_fairness_dispersion.png`](F5_fairness_dispersion.png) | `src/09_build_figures.py` | overflow-rate dispersion per level; zoom panel without B0 | `results/analysis/main_comparison.csv` |
| [`F6_checker_vs_audit.png`](F6_checker_vs_audit.png) | `src/09_build_figures.py` | the CHECKER against the audit per stratum, R1–R3 and STRESS1 (descriptive) | `results/analysis/checker_vs_audit.csv`, `results/analysis/stress1.csv` |
| [`animations/R1_net_balances.gif`](animations/R1_net_balances.gif) | `src/15_animations.py` | net beds and nurses per department and day, against the day-1 initial allocation (30 frames) | the committed run records |
| [`animations/R2_net_balances.gif`](animations/R2_net_balances.gif) | `src/15_animations.py` | net beds and nurses per department and day, against the day-1 initial allocation (30 frames) | the committed run records |
| [`animations/R3_net_balances.gif`](animations/R3_net_balances.gif) | `src/15_animations.py` | net beds and nurses per department and day, against the day-1 initial allocation (30 frames) | the committed run records |

`tests/test_report_figures.py` compares the drawn values with the table cells and the records.
