# Error analysis

*Where the errors were, and how they were found. Results only; what they imply is in [`REFLECTION.md`](REFLECTION.md). This file is **generated** by `src/16_error_analysis.py` from `src/evaluation/error_analysis_template.md`; do not edit it by hand. Every number is a table cell: a number in the text is followed by its id, which is listed with its source file in [`results/analysis/ERROR_NUMBERS.csv`](results/analysis/ERROR_NUMBERS.csv) (ids from [`ANALYSIS.md`](ANALYSIS.md) are in [`results/analysis/HEADLINE_NUMBERS.csv`](results/analysis/HEADLINE_NUMBERS.csv) too). Each error entry names where it is recorded: a claim id, a REFLECTION_LOG entry (R-number), a Decisions Log entry (Log #) or an owner decision (§11 #).*

## Summary

- **Allocation decisions (R1–R3).** Gate D passed in every run ({{n:gate_d.gate_passed.R1}}, {{n:gate_d.gate_passed.R2}}, {{n:gate_d.gate_passed.R3}}), with no Critical or Major issue ({{n:issues_by_level.Major.R1}}, {{n:issues_by_level.Major.R2}}, {{n:issues_by_level.Major.R3}} Major). The deterministic audit raised {{n:ea_d.allocation_decisions_R1_R3.deterministic_audit_or_recomputation}} issues over the three runs: nurse-gap days at Moderate, the rest Minor reversals and reallocations without effect (A1).
- **Explanation claims (R1).** {{n:ea_a2_claims.claims_scored.R1}} claims were scored: {{n:ea_a2_accuracy.wrong.pre_registered}} wrong as pre-registered, {{n:ea_a2_accuracy.wrong.after_owner_review}} after the owner review (R52). Of the confirmed errors, {{n:ea_a2_types.queue_count_wrong.claims}} are queue counts, {{n:queue_errors.L2_L1_off_by_one.claims}} of them the L2/L1 off-by-one (A2).
- **The CHECKER.** Against the audit it found {{n:checker_R1.headline_group.recall}}, {{n:checker_R2.headline_group.recall}} and {{n:checker_R3.headline_group.recall}} of the headline issues, and missed mostly reversals. On R1's wrong claims it found {{n:wrong_claims_primary.all_wrong_claims.recall}} (primary) and {{n:wrong_claims_descriptive.confirmed_wrong_claims.recall}} (descriptive), with {{n:wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes}} wrong disputes; it cannot see transcripts (A3).
- **The coding agent.** {{n:ea_b_total.cases.REFLECTION_LOG_entries}} REFLECTION_LOG entries in {{n:ea_b_total.cases.rows}} rows, in five patterns. The agent found {{n:ea_b_found_by.agent_itself.cases}} itself, the owner {{n:ea_b_found_by.owner.cases}}, independent checks {{n:ea_b_found_by.independent_check.cases}}, the test suite {{n:ea_b_found_by.test_suite.cases}}; {{n:ea_b_total.cases.with_a_rule_added}} led to a test, guard, rule or procedure (B).
- **The verification itself.** The owner's independent extraction is not a gold standard: all {{n:ea_a2_adjud.discrepancies.count}} discrepancies were attributed to the owner side, the rubric or the matching rule ({{n:ea_a2_adjud.assistant_miss.count}} assistant misses, {{n:ea_a2_adjud.assistant_encoding.count}} assistant encodings, R52), and {{n:wrong_claims_sets.rubric_dependent_spare_free.size}} pre-registered wrong claims depend only on the rubric's reading of *spare*/*free* (C).
- **How errors were found** (D): the agents' errors by the deterministic audit, the claim recomputation and the matching protocol, all independent of any LLM output; the coding agent's errors mostly by its own checks and the owner's reviews.

## A. Errors of the system's agents (in the runs)

### A1. ALLOCATOR: allocation decisions

*Found by the deterministic audit, which recomputes every day from the records and uses no LLM output (`EVALUATION_PLAN.md` §7).* Gate D and issue counts by level: [`ANALYSIS.md` §1.1–§1.2](ANALYSIS.md#11-gate-d-pre-registered-gate-37).

Audit issues by type (R1–R3, and STRESS1 as a separate probe):

{{table:ea_a1_types}}

- **No clinical bed error.** No run has a displaced, empty or shock-cut bed pair (A1 SV_B is {{n:main_headline.A1_SV_B.R1}}, {{n:main_headline.A1_SV_B.R2}} and {{n:main_headline.A1_SV_B.R3}}).
- **Moderate = nurse-gap days.** Every Moderate issue is a `nurse_gap` day with a net gap at tier 2 or tier 1 only: {{n:moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R1}}, {{n:moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R2}} and {{n:moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R3}} days.
- **Minor = reversals.** The Minor issues are bed and nurse reversals within W = 3 and reallocations without effect. Reversals have no cost in the model (`EVALUATION_PLAN.md` §3.8).
- **The R1 disagreement.** On issue counts R1 is {{n:issues_lex.issue_counts_Critical_Major_Moderate_Minor_vs_B1.R1}} than B1 (more nurse-gap days: {{n:moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R1}} against {{n:moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.B1}}); on A2 it is {{n:main_lex.A2_tier_3_2_1_vs_B1.R1}} (tier-2 SV_N {{n:main_headline.A2_SV_N_tier_2.R1}} against {{n:main_headline.A2_SV_N_tier_2.B1}}). Both readings are pre-registered; see [`ANALYSIS.md` §1.2](ANALYSIS.md#12-issue-counts-by-level-4-use-in-evaluation-item-2).
- **STRESS1.** The cut rule was followed on {{n:stress_criterion.days_meeting_the_criterion_shock_days.STRESS1}} shock days, cut {{n:stress_shock_days.day_23_executed_cut.STRESS1}} = c(t) {{n:stress_shock_days.day_23_forced_cut_c_t.STRESS1}}, no SHOCK_OVERCUT ([`ANALYSIS.md` §4](ANALYSIS.md#4-stress1-a-separate-probe-of-forced-cuts-11-7475)).

### A2. ALLOCATOR: explanation claims (R1)

*Found by recomputing every numeric claim with the what-if engine on the day's state rebuilt from the records (`claim_check.py`; no claim scored by reading), then by the owner's independent extraction of days 3, 8 and 18 and the owner's review of every wrong and unverifiable claim against the tool-returned values. The owner's verdicts and causes were proposed by an LLM advisor and accepted by the owner (R52).*

**The pipeline.** Claims scored, by basis (copied = one cell of a tool result received that day; derived = anything else, §4 item 8):

{{table:ea_a2_claims}}

**Extraction recall against the owner's independent extraction**, both ways (primary as pre-registered, final after the universe corrections of §11 #64–#66; descriptive after the adjudication of §11 #64–#67):

{{table:ea_a2_recall}}

**The discrepancies and their causes** (adjudicated, §11 #64; R52):

{{table:ea_a2_adjud}}

**Accuracy:** pre-registered against after the owner review:

{{table:ea_a2_accuracy}}

What separates the two columns: of the {{n:wrong_claims_sets.pre_registered_wrong_claims.size}} pre-registered wrong claims, {{n:wrong_claims_sets.rubric_dependent_spare_free.size}} are rubric-dependent *spare*/*free* readings, correct under the rival reading (a rubric problem, not an agent error; R42, §11 #59, part C), and {{n:wrong_claims_sets.extraction_error.size}} are extraction errors (R1-D28-05, R1-D28-06), which leaves {{n:wrong_claims_sets.confirmed_wrong.size}} confirmed errors. The unverifiable claims fall as the owner review of §11 #69 classified them.

**The confirmed errors by type** (owner typology, R52; `results/analysis/R1_owner_error_types.csv`, confirmed by the owner):

{{table:ea_a2_types}}

Within "queue count wrong": {{n:queue_errors.L2_L1_off_by_one.claims}} are the systematic L2/L1 off-by-one, {{n:queue_errors.L2_L1_swap_off_by_2.claims}} an L2/L1 swap and {{n:queue_errors.queue_total_off_by_one.claims}} queue totals off by one (computed from |stated − computed| and the levels named).

**Two cases.**

- **Day 11, self-correction.** R1-D11-08 and R1-D11-09 swap the L2 and L1 queue counts. The same explanation states them correctly later, but each sentence stays wrong as written (owner review).
- **Day 12, false self-verification.** R1-D12-19 understates the queue total by one patient (owner review). The ALLOCATOR's closing message then says the figure "matches the queue records". That sentence is in the transcript only, outside the CHECKER's information set (R66); only a transcript audit can see it.

### A3. The CHECKER

*Found by matching the CHECKER's reports against the deterministic audit on (day, type) (`EVALUATION_PLAN.md` §4 items 4–8), and by the owner-reviewed mapping of its explanation findings to R1's claims (Log #130, #134).*

**Against the audit** (per run and group: [`ANALYSIS.md` §2](ANALYSIS.md#2-the-checker-against-the-deterministic-audit-r1r3-4-items-48)). Headline group recall {{n:checker_R1.headline_group.recall}}, {{n:checker_R2.headline_group.recall}}, {{n:checker_R3.headline_group.recall}}, precision {{n:checker_R1.headline_group.precision}}, {{n:checker_R2.headline_group.precision}}, {{n:checker_R3.headline_group.precision}}; secondary group recall {{n:checker_R1.secondary_group.recall}}, {{n:checker_R2.secondary_group.recall}}, {{n:checker_R3.secondary_group.recall}}. What it missed, by type:

{{table:ea_a3_missed}}

On STRESS1 (descriptive) its headline recall is {{n:checker_STRESS1.headline_group.recall}}, with precision {{n:checker_STRESS1.headline_group.precision}}. Reversal recall measures reading of τ, not discovery (§4 item 8).

**On R1's wrong claims** ([`ANALYSIS.md` §3](ANALYSIS.md#3-the-checker-on-r1s-wrong-explanation-claims-4-claims-item-4-11-73)). Against the pre-registered set: recall {{n:wrong_claims_primary.all_wrong_claims.recall}}, precision {{n:wrong_claims_primary.all_wrong_claims.precision}}. Against the owner-confirmed set: recall {{n:wrong_claims_descriptive.confirmed_wrong_claims.recall}}, precision {{n:wrong_claims_descriptive.confirmed_wrong_claims.precision}}. By error type it caught {{n:wrong_claims_by_error_type.two_quantities_conflated.recall}} conflated quantities and {{n:wrong_claims_by_error_type.queue_count_wrong.recall}} queue counts, and none of the other types. Its {{n:wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes}} wrong disputes are on day 28 (R1-D28-28, R1-D28-29, R1-D28-30): it computed beds minus census on the day-27 allocation, and the stated figures are correct (owner review, Log #134).

**What it cannot see.** Its tools return the records, the decision history and a what-if, not the transcripts (Log #73). A false statement made outside the explanation fields, like the day-12 self-verification, is outside its information set (R66).

## B. Errors of the coding agent (Claude Code) during development

*Every REFLECTION_LOG entry in which the coding agent made an error with a consequence or a near consequence, one row each, from the whole log, first entry to last; the Decisions Log adds none that the log does not already record. Excluded: R4 (the agent answered correctly), R6 (a property of the data), R15 (an open status question), R32 and R33 (CHECKER behaviour and evaluation design, part A), R52 (a disclosure); advisor, owner and specification errors are in part C. "Rule added" means a test, a guard, a `CLAUDE.md` rule or a documented procedure that stops a recurrence.*

Counts per pattern:

{{table:ea_b_patterns}}

How they were found, and what was added:

{{table:ea_b_found_by}}

{{table:ea_b_rules}}

{{register:B}}

## C. Errors in the verification itself

*The reference is not a gold standard.* The owner's independent extraction differed from the assistant's on {{n:ea_a2_adjud.discrepancies.count}} claims. By cause: owner encoding {{n:ea_a2_adjud.owner_encoding.count}}, owner miss {{n:ea_a2_adjud.owner_miss.count}}, rubric ambiguity {{n:ea_a2_adjud.rubric_ambiguity.count}}, matching rule {{n:ea_a2_adjud.matching_rule.count}}; assistant miss {{n:ea_a2_adjud.assistant_miss.count}}, assistant encoding {{n:ea_a2_adjud.assistant_encoding.count}} (R52: causes proposed by an LLM advisor and accepted by the owner). The rubric's strict reading of *spare*/*free* made {{n:wrong_claims_sets.rubric_dependent_spare_free.size}} correct claims count as wrong (R42).

{{table:ea_c}}

{{register:C}}

## D. How each error was found

Each row is a kind of error, with its unit; each cell counts the errors of that row found by that method.

{{table:ea_d}}
