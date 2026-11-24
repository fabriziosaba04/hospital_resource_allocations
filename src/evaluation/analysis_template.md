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

{{table:gate_d}}

All three runs pass gate D: {{n:gate_d.gate_passed.R1}}, {{n:gate_d.gate_passed.R2}}, {{n:gate_d.gate_passed.R3}}. None of them is therefore counted as evidence against the hypothesis on the gate ([`plan.md`](plan.md)), and their A-metrics are interpreted. No submission was rejected and no day failed in any run (rejected submissions: {{n:gate_d.rejected_submissions.R1}}, {{n:gate_d.rejected_submissions.R2}}, {{n:gate_d.rejected_submissions.R3}}; failure days: {{n:gate_d.ALLOCATOR_failure_days.R1}}, {{n:gate_d.ALLOCATOR_failure_days.R2}}, {{n:gate_d.ALLOCATOR_failure_days.R3}}).

### 1.2 Issue counts by level (§4, "Use in evaluation" item 2)

Runs are compared on these counts lexicographically (Critical, then Major, then Moderate, then Minor), with no weighted sum. For the baselines, explanation and process items do not apply (§4 item 1).

{{table:issues_by_level}}

### 1.3 Headline metrics (§3.10)

A1 is the bed clinical gap SV_B with its split by pair type. A2 is the nurse clinical gap SV_N per tier, read lexicographically. A3 is overflow for tiers 3 and 2: raw, excess, and the avoidable and path parts. Lower is better for all of them. The floor is policy-independent, and a floor of 0 is a lower bound (§8).

{{table:main_headline}}

**Gap to B1 and to the floor** (the pre-registered reading, §1, §3.10), run by run:

{{table:main_gap}}

{{table:main_gap_summary}}

**A2 read lexicographically** (§3.2: tier 3 first, then tier 2, then tier 1):

{{table:main_lex}}

Results, run by run:

- **A1.** A1 rows with a non-zero gap to B1: {{n:main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R1}}, {{n:main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R2}} and {{n:main_gap_summary.A1_rows_with_a_non_zero_gap_to_B1.R3}}. SV_B is {{n:main_headline.A1_SV_B.R1}}, {{n:main_headline.A1_SV_B.R2}} and {{n:main_headline.A1_SV_B.R3}}. That equals B1 ({{n:main_headline.A1_SV_B.B1}}) and the floor. B1 scores 0 on A1 by construction (§3.1), so on A1 a run can match B1 but never beat it.
- **A2.** Tier 3 is {{n:main_headline.A2_SV_N_tier_3.R1}}, {{n:main_headline.A2_SV_N_tier_3.R2}} and {{n:main_headline.A2_SV_N_tier_3.R3}}, as for B1. At tier 2 the gap to B1 is {{n:main_gap.A2_SV_N_tier_2.R1_B1}}, {{n:main_gap.A2_SV_N_tier_2.R2_B1}} and {{n:main_gap.A2_SV_N_tier_2.R3_B1}}, so every run is below B1. At tier 1 it is {{n:main_gap.A2_SV_N_tier_1.R1_B1}}, {{n:main_gap.A2_SV_N_tier_1.R2_B1}} and {{n:main_gap.A2_SV_N_tier_1.R3_B1}}. Read lexicographically, each run is better than B1 on A2: {{n:main_lex.A2_tier_3_2_1_vs_B1.R1}}, {{n:main_lex.A2_tier_3_2_1_vs_B1.R2}}, {{n:main_lex.A2_tier_3_2_1_vs_B1.R3}}. B1 itself is {{n:main_headline.A2_SV_N_tier_2.B1}} above the floor of 0 at tier 2, and {{n:main_headline.A2_SV_N_tier_1.B1}} at tier 1. That is the whole headroom below B1 on this seed (`EVALUATION_PLAN.md` §8.1).
- **A3.** A3 rows with a non-zero gap to B1: {{n:main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R1}}, {{n:main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R2}} and {{n:main_gap_summary.A3_rows_with_a_non_zero_gap_to_B1.R3}}. At tier 2 each run has {{n:main_headline.A3_tier_2_path.R1}}, {{n:main_headline.A3_tier_2_path.R2}} and {{n:main_headline.A3_tier_2_path.R3}} patient-day of path excess, as B1 does ({{n:main_headline.A3_tier_2_path.B1}}).

> *Figure placeholders (Phase 3):* F1 overflow by tier with the floor (A3); F2 avoidable nurse gap by tier (A2).

### 1.4 Secondary metrics (§3.10)

**Reversals have no cost in the model.** Under no-eviction, occupied beds never move, so a policy can reduce reversals simply by leaving spare beds idle. A low reversal count is therefore not evidence of a better allocation (§3.8). W = 3 is the primary window; W = 2 and W = 5 are the pre-registered sensitivity checks. Fairness (B1–B3) is always read next to A1 and A3 (§3.5). The A4 tier floor is context for A2 (§3.4).

{{table:main_secondary}}

> *Figure placeholders (Phase 3):* F3 beds over time per policy; F4 nurses against the requirement; F5 fairness dispersion.

### 1.5 Descriptive metrics (§3.10)

RS and reallocation frequency describe how much was moved; reallocation is the task, not a cost (§3.8). C2 and C4 are already contained in A1 and A2 (§3.6).

{{table:main_descriptive}}

### 1.6 Variability across R1–R3 (§9)

With n = 3 runs, no inferential statistics are claimed (§9). Per metric: the range over R1–R3 and the mean, which is reported only because §9 defines it. Each run's value is in the tables above, and the baselines are the reference lines.

{{table:main_variability}}

**Decision-level agreement between runs** (§9: "the share of days on which the runs chose identical allocations" and "the mean L1 distance between their daily allocations"): *pending the owner's choice of the exact definition* (pairwise or all three runs; beds and nurses separately or together). It is not computed yet.

## 2. The CHECKER against the deterministic audit, R1–R3 (§4 items 4–8)

The CHECKER is blind to the audit (§11 #29). Its issues are matched to the audit's issues on (day, type). Within a key, both sides are sorted most severe first and paired in order, so when the CHECKER reports fewer issues than the audit under a key, the matched audit issues are taken to be its most severe ones. The figures are stratified by group (the headline group, with `rejected_submission` as its own row), by level and by type; the pooled figure is for reference only (§4 item 5). §4 defines no figure pooled across runs, so none is given.

Two notes go with every figure:

- **Reversal recall measures reading, not discovery** (§4 item 8). The CHECKER receives the reference allocation and τ exactly as the audit computes them.
- **Level agreement.** In R1–R3 every audit issue type comes with one level: reversals and reallocations without effect are Minor, and `nurse_gap` is Moderate because no run has a tier-3 gap. The CHECKER used the same level per type, so level agreement equals the matched count here.

Pipeline check: matched per (day, type) was recounted as min(audit, CHECKER) straight from the two record files, without the matching code, and agrees in every run (last row of the extra table).

{{table:checker_R1}}

{{table:checker_R2}}

{{table:checker_R3}}

Date-shift matches are descriptive only and never replace the primary figures (§4 item 7). LLM-only issues (explanation accuracy) are reported apart and are LLM-dependent (§4 item 4).

{{table:checker_extra}}

Headline group, run by run: {{n:checker_R1.headline_group.recall}}, {{n:checker_R2.headline_group.recall}} and {{n:checker_R3.headline_group.recall}} recall, all of it `nurse_gap` (no run has a bed clinical or hard-constraint issue). Secondary group: {{n:checker_R1.secondary_group.recall}}, {{n:checker_R2.secondary_group.recall}} and {{n:checker_R3.secondary_group.recall}}.

> *Figure placeholder (Phase 3):* F6 CHECKER against the audit, by stratum.

## 3. The CHECKER on R1's wrong explanation claims (§4 claims item 4; §11 #73)

The reference sets, side by side (§11 #73):

- **Primary:** the **{{n:wrong_claims_sets.pre_registered_wrong_claims.size}} pre-registered wrong claims**, stratified as {{n:wrong_claims_sets.rubric_dependent_spare_free.size}} rubric-dependent (*spare*/*free*) + {{n:wrong_claims_sets.extraction_error.size}} extraction errors + {{n:wrong_claims_sets.confirmed_wrong.size}} confirmed.
- **Descriptive:** the **{{n:wrong_claims_sets.confirmed_wrong_after_owner_review.size}} `confirmed_wrong`** after the owner review. **R52:** they rest on verdicts proposed by an LLM advisor and accepted by the owner.

The claims the CHECKER contested are mapped in [`results/analysis/R1_checker_dispute_mapping.json`](results/analysis/R1_checker_dispute_mapping.json). The pre-registered protocol foresees this mapping (§4 claims items 3 and 7.3). The assistant made it, after the extraction commit and the owner review, from the CHECKER's LLM-only issues on R1 ({{n:wrong_claims_sets.CHECKER_LLM_only_issues_on_R1.size}}), with the rule stated in that file.

{{table:wrong_claims_primary}}

{{table:wrong_claims_descriptive}}

*The confirmed wrong claims stratified by error type* (§11 #73): *pending the owner's definition of "error type"*. The owner-review files carry a category and a rubric tier per claim, but no error-type field.

The two cases the owner asked about:

{{table:wrong_claims_cases}}

- **The *spare*/*free* readings.** The CHECKER contested {{n:wrong_claims_cases.spare_free_rubric_dependent_claims_contested.value}} rubric-dependent claims, all three in its day-28 finding. None of its findings contests a claim on the strict reading ({{n:wrong_claims_cases.spare_free_CHECKER_findings_that_contest_a_claim_on_the_strict_reading.value}}). On day 28 it uses "beds minus census" itself, and computes it on the day-27 allocation. The decided day-28 beds minus the census give exactly the stated figures. So it contests three claims that the owner review counts as correct, and these are its {{n:wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes}} wrong disputes against the descriptive set.
- **The day-12 false self-verification.** The CHECKER contested the wrong queue total, R1-D12-19 ({{n:wrong_claims_cases.day_12_queue_total_R1_D12_19_contested.value}}). The sentence "which matches the queue records" is in the ALLOCATOR's closing message (transcript), not in its submitted explanation, and no CHECKER tool returns transcripts ({{n:wrong_claims_cases.day_12_matches_the_queue_records_visible_to_the_CHECKER.value}}).

## 4. STRESS1: a separate probe of forced cuts (§11 #74–#75)

One constructed probe (n = 1), reported as a case, with no generalisation and never pooled with R1–R3. Before any use of the shock-day pairing, the closed-form test is required (§6 item 4). It was run again here:

{{table:stress_precondition}}

**Shock days** (Σ_d O_d > P_B, which depends on each run's own holders) with the §11 #74 measures, next to the baselines on the stress variant:

{{table:stress_shock_days}}

**Criterion "follows the cut rule"** (§11 #74): on a shock day, the allocation in effect has no SHOCK_OVERCUT, its executed cut equals c(t), and the gate D components hold on that day.

{{table:stress_criterion}}

STRESS1 meets the criterion on {{n:stress_criterion.days_meeting_the_criterion_shock_days.STRESS1}} shock days, with a shock-cut severity of {{n:stress_shock_days.day_23_shock_cut_severity.STRESS1}}.

**The full §8.2 table, descriptive:**

{{table:stress_metrics}}

**The CHECKER against the audit on STRESS1** (descriptive, same procedure as §2, with shock days as their own stratum; §11 #75):

{{table:checker_STRESS1}}

{{table:checker_STRESS1_shock}}

{{table:checker_STRESS1_nonshock}}

{{table:checker_STRESS1_extra}}

On the shock day the audit has no issue and the CHECKER no matchable one (pooled shock-day recall {{n:checker_STRESS1_shock.pooled_reference_only.recall}}, precision {{n:checker_STRESS1_shock.pooled_reference_only.precision}}), so every shock-day stratum is empty. Its issues dated day 23 are LLM-only ({{n:checker_STRESS1_extra.checker_STRESS1_shock_CHECKER_LLM_only_issues.value}}, an `explanation_inaccuracy`), and STRESS1's explanation claims are not scored (§4 claims item 5).
