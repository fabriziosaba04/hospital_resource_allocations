# Analysis

*Results only; limitations and reflection come later ([`REFLECTION.md`](REFLECTION.md), [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md)). This file is **generated** by `src/14_write_analysis.py` from `src/evaluation/analysis_template.md` and the tables in [`results/analysis/`](results/analysis/); do not edit it by hand. Every number below is a cell of one of those tables. A number in the text is followed by its id in brackets, and every number appears in [`results/analysis/HEADLINE_NUMBERS.csv`](results/analysis/HEADLINE_NUMBERS.csv) with its source file and script.*

**How to read it.**

- **Numbers.** Section numbers, dates, day numbers, tiers, levels, the window W and the number of runs are labels, not results; every other number is a table cell.
- **Pre-registered or not.** The metric definitions, their roles and their reading were fixed on 2026-11-12, before any agent output ([`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) §3, §4, §9). The STRESS1 quantities and the two reference sets for R1's wrong claims were fixed before those comparisons were run ([`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) §11 #73–#75). In `HEADLINE_NUMBERS.csv`, `pre_registered` is `yes` for these and `no` for anything added in the analysis. The `role` column gives the pre-registered role: headline, gate, secondary, descriptive, context, or check (a verification output).
- **No pooled score and no combined score** (§3.10). Results are given run by run. The only cross-run quantities are the ones §9 defines: per metric, "the value for each run (R1–R3), with the range (min–max) and the mean".
- Matching figures are written as **matched/total** (§4 item 6). An en dash (–) means no floor is defined, or the item does not apply.
- **Reproduce:** `uv run python src/10_main_comparison.py`, then `11_checker_vs_audit.py`, `12_checker_on_wrong_claims.py`, `13_stress1.py` and `14_write_analysis.py`. Each script recomputes from the committed run records with no LLM output; re-running leaves `git status` clean.

## 1. Main comparison: R1–R3 against B0–B2 on `seed20261107`

The agent runs R1–R3 and the baselines B0 (no reallocation), B1 (clinical-priority-first) and B2 (proportional) all run on the primary dataset. Every metric is recomputed from each run's records with the same code (`metrics.evaluate_run`). The baseline values equal the committed ones, so they reproduce the headroom table (`EVALUATION_PLAN.md` §8.1).

### 1.1 Gate D (pre-registered gate, §3.7)

| | R1 | R2 | R3 |
| --- | --- | --- | --- |
| gate passed | yes | yes | yes |
| hard-constraint violations in effect | 0 | 0 | 0 |
| replay mismatches | 0 | 0 | 0 |
| pairing / closed-form mismatches | 0 | 0 | 0 |
| rejected submissions | 0 | 0 | 0 |
| ALLOCATOR failure days | 0 | 0 | 0 |
| halts | 0 | 0 | 0 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `gate_d.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

All three runs pass gate D: yes [`gate_d.gate_passed.R1`], yes [`gate_d.gate_passed.R2`], yes [`gate_d.gate_passed.R3`]. None of them is therefore counted as evidence against the hypothesis on the gate ([`plan.md`](plan.md)), and their A-metrics are interpreted. No submission was rejected and no day failed in any run (rejected submissions: 0 [`gate_d.rejected_submissions.R1`], 0 [`gate_d.rejected_submissions.R2`], 0 [`gate_d.rejected_submissions.R3`]; failure days: 0 [`gate_d.ALLOCATOR_failure_days.R1`], 0 [`gate_d.ALLOCATOR_failure_days.R2`], 0 [`gate_d.ALLOCATOR_failure_days.R3`]).

### 1.2 Issue counts by level (§4, "Use in evaluation" item 2)

Runs are compared on these counts lexicographically (Critical, then Major, then Moderate, then Minor), with no weighted sum. For the baselines, explanation and process items do not apply (§4 item 1).

| | R1 | R2 | R3 | B0 | B1 | B2 |
| --- | --- | --- | --- | --- | --- | --- |
| Critical | 0 | 0 | 0 | 0 | 0 | 0 |
| Major | 0 | 0 | 0 | 108 | 0 | 0 |
| Moderate | 5 | 1 | 1 | 176 | 3 | 19 |
| Minor | 96 | 91 | 85 | 0 | 92 | 93 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `issues_by_level.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

### 1.3 Headline metrics (§3.10)

A1 is the bed clinical gap SV_B with its split by pair type. A2 is the nurse clinical gap SV_N per tier, read lexicographically. A3 is overflow for tiers 3 and 2: raw, excess, and the avoidable and path parts. Lower is better for all of them. The floor is policy-independent, and a floor of 0 is a lower bound (§8).

| | R1 | R2 | R3 | B0 | B1 | B2 | floor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 SV_B | 0 | 0 | 0 | 280 | 0 | 3 | 0 |
| A1 displaced severity | 0 | 0 | 0 | 8 | 0 | 3 | 0 |
| A1 empty severity | 0 | 0 | 0 | 272 | 0 | 0 | 0 |
| A1 shock-cut severity | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A2 SV_N tier 3 | 0 | 0 | 0 | 8.8 | 0 | 0 | 0 |
| A2 SV_N tier 2 | 0.15 | 0 | 0.15 | 67.9 | 1.05 | 6.85 | 0 |
| A2 SV_N tier 1 | 1.9 | 0.9 | 0 | 65.8 | 1.2 | 0.85 | 0 |
| A3 tier 3 raw | 0 | 0 | 0 | 12 | 0 | 0 | 0 |
| A3 tier 3 excess | 0 | 0 | 0 | 12 | 0 | 0 | 0 |
| A3 tier 3 avoid | 0 | 0 | 0 | 12 | 0 | 0 | 0 |
| A3 tier 3 path | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 2 raw | 1 | 1 | 1 | 106 | 1 | 4 | 0 |
| A3 tier 2 excess | 1 | 1 | 1 | 106 | 1 | 4 | 0 |
| A3 tier 2 avoid | 0 | 0 | 0 | 106 | 0 | 3 | 0 |
| A3 tier 2 path | 1 | 1 | 1 | 0 | 1 | 1 | 0 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_headline.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**Gap to B1 and to the floor** (the pre-registered reading, §1, §3.10), run by run:

| | R1 - B1 | R2 - B1 | R3 - B1 | R1 - floor | R2 - floor | R3 - floor |
| --- | --- | --- | --- | --- | --- | --- |
| A1 SV_B | 0 | 0 | 0 | 0 | 0 | 0 |
| A1 displaced severity | 0 | 0 | 0 | 0 | 0 | 0 |
| A1 empty severity | 0 | 0 | 0 | 0 | 0 | 0 |
| A1 shock-cut severity | 0 | 0 | 0 | 0 | 0 | 0 |
| A2 SV_N tier 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| A2 SV_N tier 2 | -0.9 | -1.05 | -0.9 | 0.15 | 0 | 0.15 |
| A2 SV_N tier 1 | 0.7 | -0.3 | -1.2 | 1.9 | 0.9 | 0 |
| A3 tier 3 raw | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 3 excess | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 3 avoid | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 3 path | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 2 raw | 0 | 0 | 0 | 1 | 1 | 1 |
| A3 tier 2 excess | 0 | 0 | 0 | 1 | 1 | 1 |
| A3 tier 2 avoid | 0 | 0 | 0 | 0 | 0 | 0 |
| A3 tier 2 path | 0 | 0 | 0 | 1 | 1 | 1 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_gap.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | R1 | R2 | R3 |
| --- | --- | --- | --- |
| A1 rows with a non-zero gap to B1 | 0/4 | 0/4 | 0/4 |
| A2 rows with a non-zero gap to B1 | 2/3 | 2/3 | 2/3 |
| A3 rows with a non-zero gap to B1 | 0/8 | 0/8 | 0/8 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_gap_summary.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**A2 read lexicographically** (§3.2: tier 3 first, then tier 2, then tier 1):

| | R1 | R2 | R3 |
| --- | --- | --- | --- |
| A2 (tier 3, 2, 1) vs B0 | better | better | better |
| A2 (tier 3, 2, 1) vs B1 | better | better | better |
| A2 (tier 3, 2, 1) vs B2 | better | better | better |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_lex.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

Results, run by run:

- **A1.** A1 rows with a non-zero gap to B1: 0/4 [`main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R1`], 0/4 [`main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R2`] and 0/4 [`main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R3`]. SV_B is 0 [`main_headline.A1_SV_B.R1`], 0 [`main_headline.A1_SV_B.R2`] and 0 [`main_headline.A1_SV_B.R3`]. That equals B1 (0 [`main_headline.A1_SV_B.B1`]) and the floor. B1 is optimal on A1 by construction (§3.1), so every run reaches the optimum on A1, and no policy can exceed it.
- **A2.** Tier 3 is 0 [`main_headline.A2_SV_N_tier_3.R1`], 0 [`main_headline.A2_SV_N_tier_3.R2`] and 0 [`main_headline.A2_SV_N_tier_3.R3`], as for B1.
  - **Tier 2:** each run is below B1 by about one need unit over the horizon. The gaps to B1 are -0.9 [`main_gap.A2_SV_N_tier_2.R1_B1`], -1.05 [`main_gap.A2_SV_N_tier_2.R2_B1`] and -0.9 [`main_gap.A2_SV_N_tier_2.R3_B1`]; the gaps to the floor are 0.15 [`main_gap.A2_SV_N_tier_2.R1_floor`], 0 [`main_gap.A2_SV_N_tier_2.R2_floor`] and 0.15 [`main_gap.A2_SV_N_tier_2.R3_floor`].
  - **Tier 1:** mixed. The gaps to B1 are 0.7 [`main_gap.A2_SV_N_tier_1.R1_B1`], -0.3 [`main_gap.A2_SV_N_tier_1.R2_B1`] and -1.2 [`main_gap.A2_SV_N_tier_1.R3_B1`].
  - **Lexicographic reading** (tier 3 first, then tier 2): each run is better than B1 on A2 (better [`main_lex.A2_tier_3_2_1_vs_B1.R1`], better [`main_lex.A2_tier_3_2_1_vs_B1.R2`], better [`main_lex.A2_tier_3_2_1_vs_B1.R3`]). The difference is decided at tier 2, by the magnitudes above.
  - **Context: B1 is not an optimum on A2.** B1 is optimal on A1 by construction but greedy on nurses: it gives each department whole nurses for its incremental need, tier 3 first ([`docs/LIMITATIONS_AND_REFLECTION.md`](docs/LIMITATIONS_AND_REFLECTION.md) §4; §11 #50). REFLECTION_LOG R35 records that on the synthetic HARD10 fixture an agent run beat B1 at every A2 tier. On this seed B1 itself is 1.05 [`main_headline.A2_SV_N_tier_2.B1`] above the floor of 0 at tier 2 and 1.2 [`main_headline.A2_SV_N_tier_1.B1`] at tier 1; that is the whole headroom below B1 (`EVALUATION_PLAN.md` §8.1). Being better than B1 on A2 therefore means doing better than a greedy rule within that headroom, not beating an optimum.
- **A3.** A3 rows with a non-zero gap to B1: 0/8 [`main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R1`], 0/8 [`main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R2`] and 0/8 [`main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R3`]. At tier 2 each run has 1 [`main_headline.A3_tier_2_path.R1`], 1 [`main_headline.A3_tier_2_path.R2`] and 1 [`main_headline.A3_tier_2_path.R3`] patient-day of path excess, as B1 does (1 [`main_headline.A3_tier_2_path.B1`]).

> *Figure placeholders (Phase 3):* F1 overflow by tier with the floor (A3); F2 avoidable nurse gap by tier (A2).

### 1.4 Secondary metrics (§3.10)

**Reversals have no cost in the model.** Under no-eviction, occupied beds never move, so a policy can reduce reversals simply by leaving spare beds idle. A low reversal count is therefore not evidence of a better allocation (§3.8). W = 3 is the primary window; W = 2 and W = 5 are the pre-registered sensitivity checks. Fairness (B1–B3) is always read next to A1 and A3 (§3.5). The A4 tier floor is context for A2 (§3.4).

| | R1 | R2 | R3 | B0 | B1 | B2 | floor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E bed reversals W3 | 118 | 122 | 112 | 0 | 116 | 114 | 0 |
| E bed reversals W2 | 99 | 104 | 91 | 0 | 100 | 96 | 0 |
| E bed reversals W5 | 124 | 129 | 121 | 0 | 126 | 123 | 0 |
| E nurse reversals W3 | 52 | 44 | 43 | 0 | 47 | 48 | 0 |
| E nurse reversals W2 | 46 | 38 | 38 | 0 | 40 | 41 | 0 |
| E nurse reversals W5 | 53 | 46 | 45 | 0 | 48 | 48 | 0 |
| B1 dispersion L1 (pp) | 5.58 | 5.08 | 5.58 | 49.19 | 6.09 | 2 | – |
| B1 dispersion L2 (pp) | 0.41 | 0.24 | 0.24 | 34.37 | 0.41 | 2.1 | – |
| B1 dispersion L3 (pp) | 0 | 0 | 0 | 3.68 | 0 | 0 | – |
| B2 F1 inversions L1 | 0 | 0 | 0 | 40 | 0 | 1 | 0 |
| B2 F1 inversion wait days L1 | 0 | 0 | 0 | 89 | 0 | 1 | 0 |
| B2 F1 inversions L2 | 0 | 0 | 0 | 46 | 0 | 0 | 0 |
| B2 F1 inversion wait days L2 | 0 | 0 | 0 | 75 | 0 | 0 | 0 |
| B2 F1 inversions L3 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| B2 F1 inversion wait days L3 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| B3 mean overflow days L1 | 1 | 1 | 1 | 2.324 | 1 | 1.056 | – |
| B3 max overflow days L1 | 1 | 1 | 1 | 7 | 1 | 2 | – |
| B3 mean overflow days L2 | 1 | 1 | 1 | 2.35 | 1 | 1 | – |
| B3 max overflow days L2 | 1 | 1 | 1 | 4 | 1 | 1 | – |
| B3 mean overflow days L3 | 0 | 0 | 0 | 1.091 | 0 | 0 | – |
| B3 max overflow days L3 | 0 | 0 | 0 | 2 | 0 | 0 | – |
| A4 shortage L3 | 0 | 0 | 0 | 8.8 | 0 | 0 | – |
| A4 shortage L2 | 4.25 | 4.1 | 4.25 | 63.2 | 5.15 | 10.95 | – |
| A4 shortage L1 | 37.8 | 36.95 | 35.9 | 33.95 | 36.2 | 30.05 | – |
| A4 tier floor tier 3 | 0 | 0 | 0 | 0 | 0 | 0 | – |
| A4 tier floor tier 2 | 4.1 | 4.1 | 4.1 | 4.1 | 4.1 | 4.1 | – |
| A4 tier floor tier 1 | 38.2 | 38.2 | 38.2 | 38.2 | 38.2 | 38.2 | – |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_secondary.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

> *Figure placeholders (Phase 3):* F3 beds over time per policy; F4 nurses against the requirement; F5 fairness dispersion.

### 1.5 Descriptive metrics (§3.10)

RS and reallocation frequency describe how much was moved; reallocation is the task, not a cost (§3.8). C2 and C4 are already contained in A1 and A2 (§3.6).

| | R1 | R2 | R3 | B0 | B1 | B2 | floor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E bed RS total | 139 | 145 | 134 | 0 | 141 | 140 | – |
| E bed reallocation frequency (days) | 29 | 30 | 29 | 0 | 29 | 29 | – |
| E nurse RS total | 61 | 54 | 53 | 0 | 56 | 56 | – |
| E nurse reallocation frequency (days) | 29 | 29 | 27 | 0 | 28 | 27 | – |
| C1 bed utilisation | 0.9098 | 0.9098 | 0.9098 | 0.8533 | 0.9098 | 0.9098 | – |
| C2 avoidable idle bed-days | 0 | 0 | 0 | 162 | 0 | 0 | 0 |
| C3 nurse utilisation | 0.9818 | 0.9818 | 0.9818 | 0.9262 | 0.9818 | 0.9818 | – |
| C4 avoidable idle nurse-days | 0 | 0 | 0 | 61 | 0 | 0 | 0 |
| C4 unavoidable idle nurse-days | 20 | 20 | 20 | 20 | 20 | 20 | – |
| B4 coverage dispersion L1 | 0.0939 | 0.1069 | 0.0667 | 0.5373 | 0.1951 | 0.3844 | – |
| B4 coverage dispersion L2 | 0.0168 | 0.0276 | 0.0202 | 0.6437 | 0.0276 | 0.1149 | – |
| B4 coverage dispersion L3 | 0 | 0 | 0 | 0.045 | 0 | 0 | – |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_descriptive.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

### 1.6 Variability across R1–R3 (§9)

With n = 3 runs, no inferential statistics are claimed (§9). Per metric: the range over R1–R3 and the mean, which is reported only because §9 defines it. Each run's value is in the tables above, and the baselines are the reference lines.

| | min | max | mean |
| --- | --- | --- | --- |
| A1 SV_B | 0 | 0 | 0 |
| A1 displaced severity | 0 | 0 | 0 |
| A1 empty severity | 0 | 0 | 0 |
| A1 shock-cut severity | 0 | 0 | 0 |
| A2 SV_N tier 3 | 0 | 0 | 0 |
| A2 SV_N tier 2 | 0 | 0.15 | 0.1 |
| A2 SV_N tier 1 | 0 | 1.9 | 0.9333 |
| A3 tier 3 raw | 0 | 0 | 0 |
| A3 tier 3 excess | 0 | 0 | 0 |
| A3 tier 3 avoid | 0 | 0 | 0 |
| A3 tier 3 path | 0 | 0 | 0 |
| A3 tier 2 raw | 1 | 1 | 1 |
| A3 tier 2 excess | 1 | 1 | 1 |
| A3 tier 2 avoid | 0 | 0 | 0 |
| A3 tier 2 path | 1 | 1 | 1 |
| E bed reversals W3 | 112 | 122 | 117.3333 |
| E bed reversals W2 | 91 | 104 | 98 |
| E bed reversals W5 | 121 | 129 | 124.6667 |
| E nurse reversals W3 | 43 | 52 | 46.3333 |
| E nurse reversals W2 | 38 | 46 | 40.6667 |
| E nurse reversals W5 | 45 | 53 | 48 |
| B1 dispersion L1 (pp) | 5.08 | 5.58 | 5.4133 |
| B1 dispersion L2 (pp) | 0.24 | 0.41 | 0.2967 |
| B1 dispersion L3 (pp) | 0 | 0 | 0 |
| B2 F1 inversions L1 | 0 | 0 | 0 |
| B2 F1 inversion wait days L1 | 0 | 0 | 0 |
| B2 F1 inversions L2 | 0 | 0 | 0 |
| B2 F1 inversion wait days L2 | 0 | 0 | 0 |
| B2 F1 inversions L3 | 0 | 0 | 0 |
| B2 F1 inversion wait days L3 | 0 | 0 | 0 |
| B3 mean overflow days L1 | 1 | 1 | 1 |
| B3 max overflow days L1 | 1 | 1 | 1 |
| B3 mean overflow days L2 | 1 | 1 | 1 |
| B3 max overflow days L2 | 1 | 1 | 1 |
| B3 mean overflow days L3 | 0 | 0 | 0 |
| B3 max overflow days L3 | 0 | 0 | 0 |
| A4 shortage L3 | 0 | 0 | 0 |
| A4 shortage L2 | 4.1 | 4.25 | 4.2 |
| A4 shortage L1 | 35.9 | 37.8 | 36.8833 |
| A4 tier floor tier 3 | 0 | 0 | 0 |
| A4 tier floor tier 2 | 4.1 | 4.1 | 4.1 |
| A4 tier floor tier 1 | 38.2 | 38.2 | 38.2 |
| E bed RS total | 134 | 145 | 139.3333 |
| E bed reallocation frequency (days) | 29 | 30 | 29.3333 |
| E nurse RS total | 53 | 61 | 56 |
| E nurse reallocation frequency (days) | 27 | 29 | 28.3333 |
| C1 bed utilisation | 0.9098 | 0.9098 | 0.9098 |
| C2 avoidable idle bed-days | 0 | 0 | 0 |
| C3 nurse utilisation | 0.9818 | 0.9818 | 0.9818 |
| C4 avoidable idle nurse-days | 0 | 0 | 0 |
| C4 unavoidable idle nurse-days | 20 | 20 | 20 |
| B4 coverage dispersion L1 | 0.0667 | 0.1069 | 0.0892 |
| B4 coverage dispersion L2 | 0.0168 | 0.0276 | 0.0215 |
| B4 coverage dispersion L3 | 0 | 0 | 0 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `main_variability.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**Decision-level agreement between runs (descriptive, not pre-registered in this form).** §9 names the quantities ("the share of days on which the runs chose identical allocations" and "the mean L1 distance between their daily allocations") but not their exact form. The form below was fixed after the runs (owner, 2026-11-24; Decisions Log #131): pairwise, with beds and nurses separately. It compares the allocation in effect at the end of each day. The distance per day is the sum over departments of |x_d − y_d|. The table gives its mean over the days of the horizon, and the number of days with identical allocations.

| | identical days | mean L1 distance |
| --- | --- | --- |
| R1-R2 beds | 9/30 | 2.1333 |
| R1-R2 nurses | 22/30 | 0.5333 |
| R1-R3 beds | 8/30 | 2.3333 |
| R1-R3 nurses | 19/30 | 0.7333 |
| R2-R3 beds | 8/30 | 2.2 |
| R2-R3 nurses | 26/30 | 0.2667 |

*Source: [`results/analysis/main_comparison.csv`](results/analysis/main_comparison.csv), written by `src/10_main_comparison.py`. Each cell's id is `agreement.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

## 2. The CHECKER against the deterministic audit, R1–R3 (§4 items 4–8)

The CHECKER is blind to the audit (§11 #29). Its issues are matched to the audit's issues on (day, type). Within a key, both sides are sorted most severe first and paired in order, so when the CHECKER reports fewer issues than the audit under a key, the matched audit issues are taken to be its most severe ones. The figures are stratified by group (the headline group, with `rejected_submission` as its own row), by level and by type; the pooled figure is for reference only (§4 item 5). §4 defines no figure pooled across runs, so none is given.

Two notes go with every figure:

- **Reversal recall measures reading, not discovery** (§4 item 8). The CHECKER receives the reference allocation and τ exactly as the audit computes them.
- **Level agreement.** In R1–R3 every audit issue type comes with one level: reversals and reallocations without effect are Minor, and `nurse_gap` is Moderate because no run has a tier-3 gap. The CHECKER used the same level per type, so level agreement equals the matched count here.

Pipeline check: matched per (day, type) was recounted as min(audit, CHECKER) straight from the two record files, without the matching code, and agrees in every run (last row of the extra table).

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 4/5 | 4/4 | 4/4 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 76/96 | 76/85 | 76/76 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 4/5 | 4/4 | 4/4 |
| level Minor | 76/96 | 76/85 | 76/76 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 4/5 | 4/4 | 4/4 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 41/54 | 41/46 | 41/41 |
| type nurses_reversal | 33/40 | 33/37 | 33/33 |
| type reallocation_without_effect | 2/2 | 2/2 | 2/2 |
| pooled (reference only) | 80/101 | 80/89 | 80/80 |

*Source: [`results/analysis/checker_vs_audit.csv`](results/analysis/checker_vs_audit.csv), written by `src/11_checker_vs_audit.py`. Each cell's id is `checker_R1.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 1/1 | 1/1 | 1/1 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 73/91 | 73/78 | 73/73 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 1/1 | 1/1 | 1/1 |
| level Minor | 73/91 | 73/78 | 73/73 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 1/1 | 1/1 | 1/1 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 41/54 | 41/45 | 41/41 |
| type nurses_reversal | 29/34 | 29/30 | 29/29 |
| type reallocation_without_effect | 3/3 | 3/3 | 3/3 |
| pooled (reference only) | 74/92 | 74/79 | 74/74 |

*Source: [`results/analysis/checker_vs_audit.csv`](results/analysis/checker_vs_audit.csv), written by `src/11_checker_vs_audit.py`. Each cell's id is `checker_R2.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 1/1 | 1/1 | 1/1 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 62/85 | 62/68 | 62/62 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 1/1 | 1/1 | 1/1 |
| level Minor | 62/85 | 62/68 | 62/62 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 1/1 | 1/1 | 1/1 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 36/51 | 36/39 | 36/36 |
| type nurses_reversal | 24/32 | 24/27 | 24/24 |
| type reallocation_without_effect | 2/2 | 2/2 | 2/2 |
| pooled (reference only) | 63/86 | 63/69 | 63/63 |

*Source: [`results/analysis/checker_vs_audit.csv`](results/analysis/checker_vs_audit.csv), written by `src/11_checker_vs_audit.py`. Each cell's id is `checker_R3.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

Date-shift matches are descriptive only and never replace the primary figures (§4 item 7). LLM-only issues (explanation accuracy) are reported apart and are LLM-dependent (§4 item 4).

| | R1 | R2 | R3 |
| --- | --- | --- | --- |
| date-shift matches (1-2 days) | 4 | 1 | 3 |
| CHECKER LLM-only issues: explanation_inaccuracy | 4 | 7 | 4 |
| CHECKER LLM-only issues: information_leak | 0 | 0 | 0 |
| CHECKER LLM-only issues: inconsistency | 0 | 0 | 0 |
| CHECKER LLM-only issues: other | 1 | 0 | 0 |
| CHECKER issues with an unmatchable type or day | 0 | 0 | 0 |
| independent recount of matched per (day, type) | equal | equal | equal |

*Source: [`results/analysis/checker_vs_audit.csv`](results/analysis/checker_vs_audit.csv), written by `src/11_checker_vs_audit.py`. Each cell's id is `checker_extra.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

Summary, run by run (R1, R2, R3):

- **Headline group:** recall 4/5 [`checker_R1.headline_group.recall`], 1/1 [`checker_R2.headline_group.recall`], 1/1 [`checker_R3.headline_group.recall`]; precision 4/4 [`checker_R1.headline_group.precision`], 1/1 [`checker_R2.headline_group.precision`], 1/1 [`checker_R3.headline_group.precision`]. All of it is `nurse_gap`: no run has a bed clinical or hard-constraint issue.
- **Secondary group:** recall 76/96 [`checker_R1.secondary_group.recall`], 73/91 [`checker_R2.secondary_group.recall`], 62/85 [`checker_R3.secondary_group.recall`]; precision 76/85 [`checker_R1.secondary_group.precision`], 73/78 [`checker_R2.secondary_group.precision`], 62/68 [`checker_R3.secondary_group.precision`].

> *Figure placeholder (Phase 3):* F6 CHECKER against the audit, by stratum.

## 3. The CHECKER on R1's wrong explanation claims (§4 claims item 4; §11 #73)

The reference sets, side by side (§11 #73):

- **Primary:** the **75 [`wrong_claims_sets.pre_registered_wrong_claims.size`] pre-registered wrong claims**, stratified as 54 [`wrong_claims_sets.rubric_dependent_spare_free.size`] rubric-dependent (*spare*/*free*) + 2 [`wrong_claims_sets.extraction_error.size`] extraction errors + 19 [`wrong_claims_sets.confirmed_wrong.size`] confirmed.
- **Descriptive:** the **19 [`wrong_claims_sets.confirmed_wrong_after_owner_review.size`] `confirmed_wrong`** after the owner review. **R52:** they rest on verdicts proposed by an LLM advisor and accepted by the owner.

**The mapping is assistant-mapped and owner-reviewed (R52).** The claims the CHECKER contested are mapped in [`results/analysis/R1_checker_dispute_mapping.json`](results/analysis/R1_checker_dispute_mapping.json), with a readable copy in [`results/analysis/R1_checker_dispute_mapping.md`](results/analysis/R1_checker_dispute_mapping.md): the finding text, the claims, and why they match. The pre-registered protocol foresees this mapping (§4 claims items 3 and 7.3). The assistant made it, after the extraction commit and the owner review, from the CHECKER's explanation findings on R1 (5 [`wrong_claims_sets.CHECKER_LLM_only_issues_on_R1.size`], every issue of an LLM-only type), with the rule stated in that file. The owner reviews it.

**Definitions.** Recall = wrong claims the CHECKER contested / all wrong claims. Precision is **claim-level**, as pre-registered (§4 claims item 4): wrong claims it contested / all claims it contested. A finding that contests no figure adds nothing to either count, so precision says nothing about such findings. The findings themselves are counted below, all of them, mapped or not.

| | mapped | unmapped | total | value |
| --- | --- | --- | --- | --- |
| explanation findings | 4 | 1 | 5 |  |
| findings contesting a pre-registered wrong claim |  |  |  | 4/5 |
| findings contesting a confirmed wrong claim |  |  |  | 3/5 |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `checker_explanation_findings.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

The unmapped finding is the day-29 `other` issue: a truncated sentence in the situation field, which contests no figure. The CHECKER's other issues on R1 are of the audit's types (allocations); a keyword search of their text found none that disputes an explanation figure.

| | recall | precision | wrong disputes | contested unverifiable | disputes outside the universe |
| --- | --- | --- | --- | --- | --- |
| all wrong claims | 7/75 | 7/7 | 0 | 0 | 0 |
| rubric-dependent (spare/free) | 3/54 |  |  |  |  |
| extraction error | 0/2 |  |  |  |  |
| confirmed wrong | 4/19 |  |  |  |  |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `wrong_claims_primary.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | recall | precision | wrong disputes |
| --- | --- | --- | --- |
| confirmed wrong claims | 4/19 | 4/7 | 3 |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `wrong_claims_descriptive.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**The confirmed wrong claims by error type** (§11 #73). The typology comes from the owner review: a consultant (LLM advisor) proposed it and the owner adopts it (R52). It is kept in the owner input table [`results/analysis/R1_owner_error_types.csv`](results/analysis/R1_owner_error_types.csv), which the pipeline validates and reads but never writes. The stratification is used only once the owner has confirmed every row:

| | status |
| --- | --- |
| stratification by error type | pending: 0/19 rows confirmed |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `wrong_claims_by_error_type.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

As a **secondary breakdown**, by claim category (a topic, not an error type):

| | recall |
| --- | --- |
| empty_beds | 2/3 |
| nurse_coverage | 0/4 |
| overflow | 2/12 |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `wrong_claims_by_category.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

The two cases the owner asked about:

| | value |
| --- | --- |
| spare/free: rubric-dependent claims contested | 3/54 |
| spare/free: CHECKER findings that contest a claim on the strict reading | 0 |
| day 12: queue total R1-D12-19 contested | yes |
| day 12: 'matches the queue records' visible to the CHECKER | no |

*Source: [`results/analysis/checker_on_wrong_claims.csv`](results/analysis/checker_on_wrong_claims.csv), written by `src/12_checker_on_wrong_claims.py`. Each cell's id is `wrong_claims_cases.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

- **The *spare*/*free* readings.** The CHECKER contested 3/54 [`wrong_claims_cases.spare_free_rubric_dependent_claims_contested.value`] rubric-dependent claims, all three in its day-28 finding. None of its findings contests a claim on the strict reading (0 [`wrong_claims_cases.spare_free_CHECKER_findings_that_contest_a_claim_on_the_strict_reading.value`]). On day 28 it uses "beds minus census" itself, and computes it on the day-27 allocation. The decided day-28 beds minus the census give exactly the stated figures. So it contests three claims that the owner review counts as correct, and these are its 3 [`wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes`] wrong disputes against the descriptive set.
- **The day-12 false self-verification is not a CHECKER miss.** The CHECKER contested the wrong figure, the queue total R1-D12-19 (yes [`wrong_claims_cases.day_12_queue_total_R1_D12_19_contested.value`]). The sentence claiming that the figure "matches the queue records" is in the ALLOCATOR's closing message to the dispatcher (the transcript). It is not in the submitted explanation, and no CHECKER tool returns transcripts (no [`wrong_claims_cases.day_12_matches_the_queue_records_visible_to_the_CHECKER.value`]). The false self-verification lies outside the CHECKER's information set: only an audit of the transcripts can see it.

## 4. STRESS1: a separate probe of forced cuts (§11 #74–#75)

One constructed probe (n = 1), reported as a case, with no generalisation and never pooled with R1–R3. Before any use of the shock-day pairing, the closed-form test is required (§6 item 4). It was run again here:

| | result |
| --- | --- |
| shock-day A1 pairing = closed form (Hypothesis property test) | passed |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_precondition.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**How many shock days.** A shock day is a day when Σ_d O_d > P_B. It depends on each run's own holders, not only on the pool, so it is counted per policy and listed. The pool changes on more days than that; the context table shows the pool and the holders around every change:

| | STRESS1 | B0 | B1 | B2 |
| --- | --- | --- | --- | --- |
| shock days | 1 | 1 | 1 | 1 |
| shock days (list) | 23 | 23 | 23 | 23 |
| days with a bed-pool change | 16 21 23 26 | 16 21 23 26 | 16 21 23 26 | 16 21 23 26 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_shock_day_count.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | STRESS1 pool / occupied | B0 pool / occupied | B1 pool / occupied | B2 pool / occupied |
| --- | --- | --- | --- | --- |
| day 15 | 96 / 65 | 96 / 64 | 96 / 65 | 96 / 65 |
| day 16 | 100 / 72 | 100 / 60 | 100 / 72 | 100 / 72 |
| day 17 | 100 / 72 | 100 / 58 | 100 / 72 | 100 / 72 |
| day 20 | 100 / 73 | 100 / 63 | 100 / 73 | 100 / 73 |
| day 21 | 96 / 84 | 96 / 74 | 96 / 84 | 96 / 84 |
| day 22 | 96 / 70 | 96 / 64 | 96 / 70 | 96 / 70 |
| day 23 | 56 / 62 | 56 / 60 | 56 / 62 | 56 / 62 |
| day 24 | 56 / 43 | 56 / 42 | 56 / 43 | 56 / 43 |
| day 25 | 56 / 47 | 56 / 48 | 56 / 47 | 56 / 47 |
| day 26 | 96 / 49 | 96 / 49 | 96 / 48 | 96 / 50 |
| day 27 | 96 / 76 | 96 / 74 | 96 / 76 | 96 / 75 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_pool_context.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**Shock days with the §11 #74 measures**, next to the baselines on the stress variant:

| | STRESS1 | B0 | B1 | B2 |
| --- | --- | --- | --- | --- |
| day 23 forced cut c(t) | 6 | 4 | 6 | 6 |
| day 23 executed cut | 6 | 4 | 6 | 6 |
| day 23 shock-cut pairs | 0 | 0 | 0 | 0 |
| day 23 shock-cut severity | 0 | 0 | 0 | 0 |
| day 23 SHOCK_OVERCUT rejected | 0 | – | – | – |
| day 23 SHOCK_OVERCUT in effect | no | no | no | no |
| day 23 hard-constraint errors | 0 | 0 | 0 | 0 |
| day 23 replay ok | yes | yes | yes | yes |
| day 23 pairing / closed-form mismatches | 0 | 0 | 0 | 0 |
| day 23 follows the cut rule | yes | yes | yes | yes |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_shock_days.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**Criterion "follows the cut rule"** (§11 #74): on a shock day, the allocation in effect has no SHOCK_OVERCUT, its executed cut equals c(t), and the gate D components hold on that day.

| | STRESS1 | B0 | B1 | B2 |
| --- | --- | --- | --- | --- |
| days meeting the criterion / shock days | 1/1 | 1/1 | 1/1 | 1/1 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_criterion.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

STRESS1 meets the criterion on 1/1 [`stress_criterion.days_meeting_the_criterion_shock_days.STRESS1`] shock days, with a shock-cut severity of 0 [`stress_shock_days.day_23_shock_cut_severity.STRESS1`].

**The full §8.2 table, descriptive:**

| | STRESS1 | B0 | B1 | B2 | floor |
| --- | --- | --- | --- | --- | --- |
| gate passed (run level) | yes | yes | yes | yes |  |
| A1 SV_B | 0 | 231 | 0 | 11 | 0 |
| A1 displaced severity | 0 | 8 | 0 | 11 | 0 |
| A1 empty severity | 0 | 223 | 0 | 0 | 0 |
| A1 shock-cut severity | 0 | 0 | 0 | 0 | 0 |
| A2 SV_N tier 3 | 0 | 8.8 | 0 | 0 | 0 |
| A2 SV_N tier 2 | 0.1 | 67.9 | 1.05 | 6.85 | 0 |
| A2 SV_N tier 1 | 1.3 | 65.8 | 1.2 | 0.85 | 0 |
| A3 tier 3 raw | 3 | 20 | 3 | 12 | 0 |
| A3 tier 3 excess | 3 | 20 | 3 | 12 | 0 |
| A3 tier 3 avoid | 0 | 17 | 0 | 9 | 0 |
| A3 tier 3 path | 3 | 3 | 3 | 3 | 0 |
| A3 tier 2 raw | 38 | 108 | 38 | 42 | 38 |
| A3 tier 2 excess | 0 | 70 | 0 | 4 | 0 |
| A3 tier 2 avoid | 0 | 69 | 0 | 2 | 0 |
| A3 tier 2 path | 0 | 1 | 0 | 2 | 0 |
| E bed reversals W3 | 116 | 0 | 115 | 104 | 0 |
| E bed reversals W2 | 100 | 0 | 100 | 90 | 0 |
| E bed reversals W5 | 123 | 0 | 124 | 115 | 0 |
| E nurse reversals W3 | 49 | 0 | 47 | 48 | 0 |
| E nurse reversals W2 | 42 | 0 | 40 | 41 | 0 |
| E nurse reversals W5 | 51 | 0 | 48 | 48 | 0 |
| B1 dispersion L1 (pp) | 3.94 | 42 | 6.45 | 7.37 | – |
| B1 dispersion L2 (pp) | 1.82 | 22.85 | 2.21 | 4.36 | – |
| B1 dispersion L3 (pp) | 0.74 | 4.29 | 0.74 | 1.59 | – |
| B2 F1 inversions L1 | 0 | 39 | 0 | 4 | 0 |
| B2 F1 inversion wait days L1 | 0 | 86 | 0 | 9 | 0 |
| B2 F1 inversions L2 | 0 | 33 | 0 | 3 | 0 |
| B2 F1 inversion wait days L2 | 0 | 57 | 0 | 4 | 0 |
| B2 F1 inversions L3 | 0 | 2 | 0 | 2 | 0 |
| B2 F1 inversion wait days L3 | 0 | 2 | 0 | 2 | 0 |
| B3 mean overflow days L1 | 1.537 | 2.156 | 1.537 | 1.513 | – |
| B3 max overflow days L1 | 3 | 7 | 3 | 3 | – |
| B3 mean overflow days L2 | 1.25 | 1.833 | 1.25 | 1.25 | – |
| B3 max overflow days L2 | 2 | 5 | 2 | 3 | – |
| B3 mean overflow days L3 | 1 | 1.111 | 1 | 1.2 | – |
| B3 max overflow days L3 | 1 | 2 | 1 | 2 | – |
| A4 shortage L3 | 0 | 8.8 | 0 | 0 | – |
| A4 shortage L2 | 4.2 | 63.2 | 5.15 | 10.95 | – |
| A4 shortage L1 | 37.25 | 33.95 | 36.2 | 30.05 | – |
| A4 tier floor tier 3 | 0 | 0 | 0 | 0 | – |
| A4 tier floor tier 2 | 4.1 | 4.1 | 4.1 | 4.1 | – |
| A4 tier floor tier 1 | 38.2 | 38.2 | 38.2 | 38.2 | – |
| E bed RS total | 142 | 0 | 142 | 133 | – |
| E bed reallocation frequency (days) | 28 | 0 | 28 | 28 | – |
| E nurse RS total | 58 | 0 | 56 | 56 | – |
| E nurse reallocation frequency (days) | 29 | 0 | 28 | 27 | – |
| C1 bed utilisation | 0.9112 | 0.859 | 0.9112 | 0.9112 | – |
| C2 avoidable idle bed-days | 0 | 145 | 0 | 0 | 0 |
| C3 nurse utilisation | 0.9818 | 0.9262 | 0.9818 | 0.9818 | – |
| C4 avoidable idle nurse-days | 0 | 61 | 0 | 0 | 0 |
| C4 unavoidable idle nurse-days | 20 | 20 | 20 | 20 | – |
| B4 coverage dispersion L1 | 0.0988 | 0.5373 | 0.1951 | 0.3844 | – |
| B4 coverage dispersion L2 | 0.0236 | 0.6437 | 0.0276 | 0.1149 | – |
| B4 coverage dispersion L3 | 0 | 0.045 | 0 | 0 | – |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `stress_metrics.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

**The CHECKER against the audit on STRESS1** (descriptive, same procedure as §2, with shock days as their own stratum; §11 #75):

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 2/4 | 2/2 | 2/2 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 58/95 | 58/68 | 58/58 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 2/4 | 2/2 | 2/2 |
| level Minor | 58/95 | 58/68 | 58/58 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 2/4 | 2/2 | 2/2 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 31/55 | 31/36 | 31/31 |
| type nurses_reversal | 25/38 | 25/30 | 25/25 |
| type reallocation_without_effect | 2/2 | 2/2 | 2/2 |
| pooled (reference only) | 60/99 | 60/70 | 60/60 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `checker_STRESS1.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 0/0 | 0/0 | 0/0 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 0/0 | 0/0 | 0/0 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 0/0 | 0/0 | 0/0 |
| level Minor | 0/0 | 0/0 | 0/0 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 0/0 | 0/0 | 0/0 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 0/0 | 0/0 | 0/0 |
| type nurses_reversal | 0/0 | 0/0 | 0/0 |
| type reallocation_without_effect | 0/0 | 0/0 | 0/0 |
| pooled (reference only) | 0/0 | 0/0 | 0/0 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `checker_STRESS1_shock.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | recall | precision | level agreement |
| --- | --- | --- | --- |
| headline group | 2/4 | 2/2 | 2/2 |
| rejected_submission (own row) | 0/0 | 0/0 | 0/0 |
| secondary group | 58/95 | 58/68 | 58/58 |
| level Critical | 0/0 | 0/0 | 0/0 |
| level Major | 0/0 | 0/0 | 0/0 |
| level Moderate | 2/4 | 2/2 | 2/2 |
| level Minor | 58/95 | 58/68 | 58/58 |
| type hard_constraint_in_effect | 0/0 | 0/0 | 0/0 |
| type rejected_submission | 0/0 | 0/0 | 0/0 |
| type allocator_failure_day | 0/0 | 0/0 | 0/0 |
| type bed_displaced | 0/0 | 0/0 | 0/0 |
| type bed_empty | 0/0 | 0/0 | 0/0 |
| type bed_shock_cut | 0/0 | 0/0 | 0/0 |
| type nurse_gap | 2/4 | 2/2 | 2/2 |
| type f1_inversion | 0/0 | 0/0 | 0/0 |
| type beds_reversal | 31/55 | 31/36 | 31/31 |
| type nurses_reversal | 25/38 | 25/30 | 25/25 |
| type reallocation_without_effect | 2/2 | 2/2 | 2/2 |
| pooled (reference only) | 60/99 | 60/70 | 60/60 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `checker_STRESS1_nonshock.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

| | value |
| --- | --- |
| checker_STRESS1_shock: days | 23 |
| checker_STRESS1_shock: CHECKER LLM-only issues | 1 |
| checker_STRESS1_nonshock: days | 29 days |
| checker_STRESS1_nonshock: CHECKER LLM-only issues | 9 |
| date-shift matches (1-2 days) | 7 |
| CHECKER LLM-only issues: explanation_inaccuracy | 10 |
| CHECKER LLM-only issues: information_leak | 0 |
| CHECKER LLM-only issues: inconsistency | 0 |
| CHECKER LLM-only issues: other | 0 |

*Source: [`results/analysis/stress1.csv`](results/analysis/stress1.csv), written by `src/13_stress1.py`. Each cell's id is `checker_STRESS1_extra.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/HEADLINE_NUMBERS.csv`.*

On the shock day the audit has no issue and the CHECKER no matchable one (pooled shock-day recall 0/0 [`checker_STRESS1_shock.pooled_reference_only.recall`], precision 0/0 [`checker_STRESS1_shock.pooled_reference_only.precision`]), so every shock-day stratum is empty. Its issues dated day 23 are LLM-only (1 [`checker_STRESS1_extra.checker_STRESS1_shock_CHECKER_LLM_only_issues.value`], an `explanation_inaccuracy`), and STRESS1's explanation claims are not scored (§4 claims item 5).
