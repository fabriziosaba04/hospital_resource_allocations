# Analysis

Cross-run results, written by the numbered entry scripts and read by [`ANALYSIS.md`](../../ANALYSIS.md). Each table is in long format, one row per reported number (`id, table, row, col, value, role, pre_registered, note`; `src/evaluation/analysis.py`).

| File | Written by | Content |
| --- | --- | --- |
| `main_comparison.csv` | `src/10_main_comparison.py` | Gate D, issue counts by level, every §3 metric of R1–R3 next to B0–B2 and the floor, gaps to B1 and to the floor, A2 lexicographic, variability (§9) |
| `checker_vs_audit.csv` | `src/11_checker_vs_audit.py` | The CHECKER against the deterministic audit, R1–R3, stratified (§4 items 4–8) |
| `checker_on_wrong_claims.csv` | `src/12_checker_on_wrong_claims.py` | The CHECKER on R1's wrong explanation claims (§11 #73) |
| `stress1.csv` | `src/13_stress1.py` | The STRESS1 probe (§11 #74–#75), incl. the shock-day closed-form test |
| `R1_checker_dispute_mapping.json` | by hand (the assistant, 2026-11-24) | Input of step 12: the claims each CHECKER finding contests, with the rule and a reason per finding |
| `R1_checker_dispute_mapping.md` | `src/12_checker_on_wrong_claims.py` | Readable copy of the mapping, for the owner's review (generated; edit the JSON) |
| `R1_owner_error_types.csv` | owner input table (pre-filled by the assistant from the owner review, confirmed by the owner) | Error type of each of the 19 confirmed wrong claims (§11 #73, R52); validated and read by step 12, never written by the pipeline |
| `HEADLINE_NUMBERS.csv` | `src/14_write_analysis.py` | Every number in `ANALYSIS.md`: `id, value, source_file, script, pre_registered, role, label` |

`recomputed/` (not committed, see `.gitignore`) receives what the numbered scripts in `src/` recompute from the run records; each script compares its output with the committed file.
