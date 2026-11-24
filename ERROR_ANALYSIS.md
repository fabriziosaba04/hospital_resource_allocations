# Error analysis

*Where the errors were, and how they were found. Results only; what they imply is in [`REFLECTION.md`](REFLECTION.md). This file is **generated** by `src/16_error_analysis.py` from `src/evaluation/error_analysis_template.md`; do not edit it by hand. Every number is a table cell: a number in the text is followed by its id, which is listed with its source file in [`results/analysis/ERROR_NUMBERS.csv`](results/analysis/ERROR_NUMBERS.csv) (ids from [`ANALYSIS.md`](ANALYSIS.md) are in [`results/analysis/HEADLINE_NUMBERS.csv`](results/analysis/HEADLINE_NUMBERS.csv) too). Each error entry names where it is recorded: a claim id, a REFLECTION_LOG entry (R-number), a Decisions Log entry (Log #) or an owner decision (§11 #).*

## Summary

- **Allocation decisions (R1–R3).** Gate D passed in every run (yes [`gate_d.gate_passed.R1`], yes [`gate_d.gate_passed.R2`], yes [`gate_d.gate_passed.R3`]), with no Critical or Major issue (0 [`issues_by_level.Major.R1`], 0 [`issues_by_level.Major.R2`], 0 [`issues_by_level.Major.R3`] Major). The deterministic audit raised 279 [`ea_d.allocation_decisions_R1_R3.deterministic_audit_or_recomputation`] issues over the three runs: nurse-gap days at Moderate, the rest Minor reversals and reallocations without effect (A1).
- **Explanation claims (R1).** 1049 [`ea_a2_claims.claims_scored.R1`] claims were scored: 75 [`ea_a2_accuracy.wrong.pre_registered`] wrong as pre-registered, 19 [`ea_a2_accuracy.wrong.after_owner_review`] after the owner review (R52). Of the confirmed errors, 11 [`ea_a2_types.queue_count_wrong.claims`] are queue counts, 7/11 [`queue_errors.L2_L1_off_by_one.claims`] of them the L2/L1 off-by-one (A2).
- **The CHECKER.** Against the audit it found 4/5 [`checker_R1.headline_group.recall`], 1/1 [`checker_R2.headline_group.recall`] and 1/1 [`checker_R3.headline_group.recall`] of the headline issues, and missed mostly reversals. On R1's wrong claims it found 7/75 [`wrong_claims_primary.all_wrong_claims.recall`] (primary) and 4/19 [`wrong_claims_descriptive.confirmed_wrong_claims.recall`] (descriptive), with 3 [`wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes`] wrong disputes; it cannot see transcripts (A3).
- **The coding agent.** 56 [`ea_b_total.cases.REFLECTION_LOG_entries`] REFLECTION_LOG entries in 54 [`ea_b_total.cases.rows`] rows, in five patterns. The agent found 30 [`ea_b_found_by.agent_itself.cases`] itself, the owner 11 [`ea_b_found_by.owner.cases`], independent checks 6 [`ea_b_found_by.independent_check.cases`], the test suite 5 [`ea_b_found_by.test_suite.cases`]; 31 [`ea_b_total.cases.with_a_rule_added`] led to a test, guard, rule or procedure (B).
- **The verification itself.** The owner's independent extraction is not a gold standard: all 43 [`ea_a2_adjud.discrepancies.count`] discrepancies were attributed to the owner side or the rubric (0 [`ea_a2_adjud.assistant_miss.count`] assistant misses, 0 [`ea_a2_adjud.assistant_encoding.count`] assistant encodings, R52), and 54 [`wrong_claims_sets.rubric_dependent_spare_free.size`] pre-registered wrong claims depend only on the rubric's reading of *spare*/*free* (C).
- **How errors were found** (D): the agents' errors by the deterministic audit, the claim recomputation and the matching protocol, all independent of any LLM output; the coding agent's errors mostly by its own checks and the owner's reviews.

## A. Errors of the system's agents (in the runs)

### A1. ALLOCATOR: allocation decisions

*Found by the deterministic audit, which recomputes every day from the records and uses no LLM output (`EVALUATION_PLAN.md` §7).* Gate D and issue counts by level: [`ANALYSIS.md` §1.1–§1.2](ANALYSIS.md#11-gate-d-pre-registered-gate-37).

Audit issues by type (R1–R3, and STRESS1 as a separate probe):

| | R1 | R2 | R3 | STRESS1 |
| --- | --- | --- | --- | --- |
| nurse_gap | 5 | 1 | 1 | 4 |
| beds_reversal | 54 | 54 | 51 | 55 |
| nurses_reversal | 40 | 34 | 32 | 38 |
| reallocation_without_effect | 2 | 3 | 2 | 2 |
| total | 101 | 92 | 86 | 99 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a1_types.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

- **No clinical bed error.** No run has a displaced, empty or shock-cut bed pair (A1 SV_B is 0 [`main_headline.A1_SV_B.R1`], 0 [`main_headline.A1_SV_B.R2`] and 0 [`main_headline.A1_SV_B.R3`]).
- **Moderate = nurse-gap days.** Every Moderate issue is a `nurse_gap` day with a net gap at tier 2 or tier 1 only: 5 [`moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R1`], 1 [`moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R2`] and 1 [`moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R3`] days.
- **Minor = reversals.** The Minor issues are bed and nurse reversals within W = 3 and reallocations without effect. Reversals have no cost in the model (`EVALUATION_PLAN.md` §3.8).
- **The R1 disagreement.** On issue counts R1 is worse [`issues_lex.issue_counts_Critical_Major_Moderate_Minor_vs_B1.R1`] than B1 (more nurse-gap days: 5 [`moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.R1`] against 3 [`moderate_issues.nurse_gap_issues_days_with_a_net_nurse_gap_at_tier_2_or_1_only.B1`]); on A2 it is better [`main_lex.A2_tier_3_2_1_vs_B1.R1`] (tier-2 SV_N 0.15 [`main_headline.A2_SV_N_tier_2.R1`] against 1.05 [`main_headline.A2_SV_N_tier_2.B1`]). Both readings are pre-registered; see [`ANALYSIS.md` §1.2](ANALYSIS.md#12-issue-counts-by-level-4-use-in-evaluation-item-2).
- **STRESS1.** The cut rule was followed on 1/1 [`stress_criterion.days_meeting_the_criterion_shock_days.STRESS1`] shock days, cut 6 [`stress_shock_days.day_23_executed_cut.STRESS1`] = c(t) 6 [`stress_shock_days.day_23_forced_cut_c_t.STRESS1`], no SHOCK_OVERCUT ([`ANALYSIS.md` §4](ANALYSIS.md#4-stress1-a-separate-probe-of-forced-cuts-11-7475)).

### A2. ALLOCATOR: explanation claims (R1)

*Found by recomputing every numeric claim with the what-if engine on the day's state rebuilt from the records (`claim_check.py`; no claim scored by reading), then by the owner's independent extraction of days 3, 8 and 18 and the owner's review of every wrong and unverifiable claim against the tool-returned values. The owner's verdicts and causes were proposed by an LLM advisor and accepted by the owner (R52).*

**The pipeline.** Claims scored, by basis (copied = one cell of a tool result received that day; derived = anything else, §4 item 8):

| | R1 |
| --- | --- |
| claims scored | 1049 |
| copied claims | 538 |
| derived claims | 511 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a2_claims.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

**Extraction recall against the owner's independent extraction**, both ways (primary as pre-registered, final after the universe corrections of §11 #64–#66; descriptive after the adjudication of §11 #64–#67):

| | primary (final) | descriptive (after adjudication) |
| --- | --- | --- |
| owner's claims found by the assistant, copied | 58/60 | 60/60 |
| owner's claims found by the assistant, derived | 27/40 | 37/40 |
| assistant's claims found by the owner, copied | 56/57 | 57/57 |
| assistant's claims found by the owner, derived | 29/49 | 41/49 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a2_recall.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

**The discrepancies and their causes** (adjudicated, §11 #64; R52):

| | count |
| --- | --- |
| discrepancies | 43 |
| owner_encoding | 28 |
| owner_miss | 7 |
| rubric_ambiguity | 6 |
| matching_rule | 2 |
| assistant_miss | 0 |
| assistant_encoding | 0 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a2_adjud.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

**Accuracy:** pre-registered against after the owner review:

| | pre-registered | after owner review |
| --- | --- | --- |
| correct | 948 | 1015 |
| wrong | 75 | 19 |
| unverifiable | 26 | 15 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a2_accuracy.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

What separates the two columns: of the 75 [`wrong_claims_sets.pre_registered_wrong_claims.size`] pre-registered wrong claims, 54 [`wrong_claims_sets.rubric_dependent_spare_free.size`] are rubric-dependent *spare*/*free* readings, correct under the rival reading (a rubric problem, not an agent error; R42, §11 #59, part C), and 2 [`wrong_claims_sets.extraction_error.size`] are extraction errors (R1-D28-05, R1-D28-06), which leaves 19 [`wrong_claims_sets.confirmed_wrong.size`] confirmed errors. The unverifiable claims fall as the owner review of §11 #69 classified them.

**The confirmed errors by type** (owner typology, R52; `results/analysis/R1_owner_error_types.csv`, confirmed by the owner):

| | claims | claim ids |
| --- | --- | --- |
| queue count wrong | 11 | D11-08 D11-09 D12-19 D12-20 D15-20 D15-21 D17-19 D17-20 D18-14 D20-33 D20-34 |
| two quantities conflated | 2 | D11-28 D13-30 |
| arithmetic slip | 1 | D21-35 |
| sign error | 1 | D17-47 |
| wrong tier/level | 2 | D28-26 D28-27 |
| claim not simulated | 1 | D27-41 |
| approximation off | 1 | D26-38 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a2_types.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

Within "queue count wrong": 7/11 [`queue_errors.L2_L1_off_by_one.claims`] are the systematic L2/L1 off-by-one, 2/11 [`queue_errors.L2_L1_swap_off_by_2.claims`] an L2/L1 swap and 2/11 [`queue_errors.queue_total_off_by_one.claims`] queue totals off by one (computed from |stated − computed| and the levels named).

**Two cases.**

- **Day 11, self-correction.** R1-D11-08 and R1-D11-09 swap the L2 and L1 queue counts. The same explanation states them correctly later, but each sentence stays wrong as written (owner review).
- **Day 12, false self-verification.** R1-D12-19 understates the queue total by one patient (owner review). The ALLOCATOR's closing message then says the figure "matches the queue records". That sentence is in the transcript only, outside the CHECKER's information set (R66); only a transcript audit can see it.

### A3. The CHECKER

*Found by matching the CHECKER's reports against the deterministic audit on (day, type) (`EVALUATION_PLAN.md` §4 items 4–8), and by the owner-reviewed mapping of its explanation findings to R1's claims (Log #130, #134).*

**Against the audit** (per run and group: [`ANALYSIS.md` §2](ANALYSIS.md#2-the-checker-against-the-deterministic-audit-r1r3-4-items-48)). Headline group recall 4/5 [`checker_R1.headline_group.recall`], 1/1 [`checker_R2.headline_group.recall`], 1/1 [`checker_R3.headline_group.recall`], precision 4/4 [`checker_R1.headline_group.precision`], 1/1 [`checker_R2.headline_group.precision`], 1/1 [`checker_R3.headline_group.precision`]; secondary group recall 76/96 [`checker_R1.secondary_group.recall`], 73/91 [`checker_R2.secondary_group.recall`], 62/85 [`checker_R3.secondary_group.recall`]. What it missed, by type:

| | R1 | R2 | R3 | STRESS1 |
| --- | --- | --- | --- | --- |
| nurse_gap | 1 | 0 | 0 | 2 |
| beds_reversal | 13 | 13 | 15 | 24 |
| nurses_reversal | 7 | 5 | 8 | 13 |
| reallocation_without_effect | 0 | 0 | 0 | 0 |
| total missed | 21 | 18 | 23 | 39 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_a3_missed.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

On STRESS1 (descriptive) its headline recall is 2/4 [`checker_STRESS1.headline_group.recall`], with precision 2/2 [`checker_STRESS1.headline_group.precision`]. Reversal recall measures reading of τ, not discovery (§4 item 8).

**On R1's wrong claims** ([`ANALYSIS.md` §3](ANALYSIS.md#3-the-checker-on-r1s-wrong-explanation-claims-4-claims-item-4-11-73)). Against the pre-registered set: recall 7/75 [`wrong_claims_primary.all_wrong_claims.recall`], precision 7/7 [`wrong_claims_primary.all_wrong_claims.precision`]. Against the owner-confirmed set: recall 4/19 [`wrong_claims_descriptive.confirmed_wrong_claims.recall`], precision 4/7 [`wrong_claims_descriptive.confirmed_wrong_claims.precision`]. By error type it caught 2/2 [`wrong_claims_by_error_type.two_quantities_conflated.recall`] conflated quantities and 2/11 [`wrong_claims_by_error_type.queue_count_wrong.recall`] queue counts, and none of the other types. Its 3 [`wrong_claims_descriptive.confirmed_wrong_claims.wrong_disputes`] wrong disputes are on day 28 (R1-D28-28, R1-D28-29, R1-D28-30): it computed beds minus census on the day-27 allocation, and the stated figures are correct (owner review, Log #134).

**What it cannot see.** Its tools return the records, the decision history and a what-if, not the transcripts (Log #73). A false statement made outside the explanation fields, like the day-12 self-verification, is outside its information set (R66).

## B. Errors of the coding agent (Claude Code) during development

*Every REFLECTION_LOG entry in which the coding agent made an error with a consequence or a near consequence, one row each, from the whole log, first entry to last; the Decisions Log adds none that the log does not already record. Excluded: R4 (the agent answered correctly), R6 (a property of the data), R15 (an open status question), R32 and R33 (CHECKER behaviour and evaluation design, part A), R52 (a disclosure); advisor, owner and specification errors are in part C. "Rule added" means a test, a guard, a `CLAUDE.md` rule or a documented procedure that stops a recurrence.*

Counts per pattern:

| | cases | with a rule added |
| --- | --- | --- |
| Silent errors (no failing signal when made) | 12 | 10 |
| False or unchecked premises | 12 | 7 |
| Scope underestimates | 10 | 9 |
| Hand-off and state errors | 6 | 1 |
| Presentation and reporting errors | 14 | 4 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_b_patterns.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

How they were found, and what was added:

| | cases |
| --- | --- |
| test suite | 5 |
| owner | 11 |
| consultant review | 0 |
| visual inspection | 1 |
| agent itself | 30 |
| independent check | 6 |
| failure in use | 1 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_b_found_by.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

| | cases |
| --- | --- |
| test | 17 |
| guard | 5 |
| CLAUDE.md | 2 |
| procedure | 7 |
| none | 23 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_b_rules.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

**Silent errors (no failing signal when made)**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R21 | Tool exceptions reached the agents as a generic error, without the state machine's message; the unit tests passed because they bypass the MCP transport | MCP server | raw JSON-RPC exchange before the smoke test | independent check | near miss: agents could not have corrected wrong-phase calls | errors converted to ToolError with their message (Log #62) | procedure |
| R23 | Occupied-reversal count not monotone in W; W = 3 values reported without reading the sensitivity columns | metric definition (Log #59) | reading the W = 2/3/5 columns | agent itself | count dropped before any agent output | §11 #32 | none |
| R26 | Taxonomy-coverage test extracted types by regex and checked 6 of 11 while passing | tests | printing the extracted set | agent itself | near miss | explicit list of the 11 types | test |
| R37 | In a fresh clone the role servers did not start; the launcher still recorded exit 0 and 'consistent' | launcher, run clone | resume test in the clone on synthetic data | independent check | near miss: a stalled run looked clean | refused spawns counted, exit 1 unless FINISHED; trust step (Log #94) | guard |
| R50 | Owner verdicts would have been typed into files the converter regenerates, and erased on rerun | owner_claims outputs | before the first rerun | agent itself | near miss | owner input tables re-applied after regeneration (Log #106, §11 #62) | test |
| R53 | Commit made through `pytest \| tail`, so it went in with two failing tests | commit 009e156 | reading the summary line after the commit | agent itself | two failing tests in history | commits gated on pytest's own exit status | CLAUDE.md |
| R54 | Display file labelled cardiology and internal medicine the wrong way round (order of a shared constant) | unverifiable_view.py | cross-check against a scratch run naming departments explicitly | independent check | faulty file never committed | labels keyed by name, test pins them | test |
| R55 | Pre-flight comparison read fields that do not exist and reported 'same: True' | run-settings comparison script | the script also printed the record keys | agent itself | result discarded before reporting | redone on the real fields | none |
| R58 | First long-path fix kept '..' unresolved and wrapped public attributes of Store | src/utils/paths.py | re-reading the helper; a fast-suite test | agent itself | none (no caller passed '..') | os.path.abspath, tests for '..' and idempotence | test |
| R59 | Evaluation entry points defaulted to writing into the frozen run folders | metrics, run_report, claim_check, src.evaluation | reading the writers during the clean-up audit | agent itself | near miss: nothing was run with the defaults | frozen-run guard; recomputation defaults (Log #119-#120) | guard |
| R61 | A fast-suite test rewrote a committed R1 file on every run, byte-identically, so git status stayed clean | tests/test_long_paths.py | reading the tests while adding the guard | agent itself | writes into a frozen folder, no change in content | test uses a temporary copy; the guard raises on the committed folder | guard |
| R68 | New block placed in the wrong branch produced no rows once the owner table was confirmed | src/12_checker_on_wrong_claims.py | expected rows missing from the printed output | agent itself | near miss | block moved; ANALYSIS.md now references its ids | test |

**False or unchecked premises**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2 | Floating-point example given to justify exact arithmetic was false | Log #29 | evaluating the example while writing the N1 test | agent itself | a correct decision rested on a false justification | example corrected; real failing cases tested (Log #42) | test |
| R3 | Property test mutated the wrong department, so the validator looked wrong | tests | Hypothesis counterexample analysed before any code change | test suite | near miss: the validator could have been weakened | only the test changed | none |
| R17 | A2 closed form missing a case; a brute-force cross-check was claimed before it was run | metric proposal | owner's review before any code | owner | would have overstated MaxN in a pre-registered metric | three-case form; enumeration cross-check (Log #46) | test |
| R18 | Hand-computed test expectation mis-ranked fractional parts | tests | the test failed on its first run | test suite | none | test corrected | none |
| R22 | Smoke test assumed the dispatcher would follow a one-off prompt; it refused and ran the draft prompts | smoke-test design | transcript classification of the smoke script | independent check | draft prompts ran on a synthetic fixture, against the owner's instruction | redesigned smoke test and probe fixture (Log #69, #70, #75) | procedure |
| R25 | Design gave the CHECKER the audit and the ALLOCATOR's what-if the violation counts | AGENTS.md, server, prompts | owner's review of the prompts | owner | matching would have measured copying | tools removed (Log #71-#74, §11 #29) | test |
| R28 | Reversal definition required a reference allocation the CHECKER could not compute | checker.md | CHECKER-vs-audit matching on the dry run | independent check | reversal recall would have measured arithmetic | reference allocation and tau supplied (§11 #36) | none |
| R31 | Hard fixture said to 'guarantee' a forced cut, which depends on the policy | HARD10 fixture | probing the draft under B0-B2 | agent itself | near miss | guarantee stated as a bound in the test (Log #88) | test |
| R34 | Synced-folder guard treated a missing manifest as 'not frozen' (fail open) | launcher guard | unit test: DID NOT RAISE | test suite | near miss | guard fails closed (Log #90) | guard |
| R35 | 'B1 is near-optimal on nurses' used as a framing without a stated scope | framing (§11 #24) | B1 against DRY2 on HARD10, then B1's gap per tier on the seeds | owner | framing false on HARD10; holds on the seeds only as a measured gap | wording scoped to A2 on the frozen seeds (§11 #50) | procedure |
| R45 | Code change scheduled on an unchecked assumption about the what-if engine | session log 'Next' | probe over all R1 claims before changing code | agent itself | none | probe recorded; change kept as defensive (Log #100) | none |
| R46 | Test assertion written from memory of an earlier output | tests/test_owner_claims.py | the test failed | test suite | none | assertion from the current output | none |

**Scope underestimates**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R5 | Run-session deny list left Monte Carlo outputs, tests/ and .hypothesis/ readable | .claude/run-settings.json | headless run-session probe | independent check | hidden generation information reachable (before any run) | deny-by-default; probe before every run | CLAUDE.md |
| R19 | Metric proposal did not flag that bed reversals reward leaving empty beds | metric proposal | baseline headroom review required by the owner | owner | a headline metric could have been gamed | stability demoted to secondary (§11 #26) | procedure |
| R20 | Committed baseline records reopened a read path to future information | .claude/run-settings.json | checking deny rules against new files before committing | agent itself | near miss | Read(./results/**) denied; probe extended (Log #60) | guard |
| R29 | Synthetic fixture never exercised clinical-priority detection | SMOKE5 dry run | per-day issue table of the dry-run report | agent itself | CHECKER detection untested on positives | harder fixture HARD10 (Log #88) | test |
| R36 | Run report would have shifted every day after a usage-limit cutoff | run_report.transcript_stats | reading the resume path | agent itself | near miss | day from the last orchestration result; numeric sort (Log #92) | test |
| R38 | Wall clock counted the night between launches; a killed launch's cost disappeared | run_report | reading the live report after copy-back | agent itself | near miss on DRY3 (synthetic) | wall clock inside launches; null cost shown (Log #96) | none |
| R40 | Copy-back left out the subagent transcripts Claude Code writes elsewhere | copy_back | listing the files the extraction may read | agent itself | evidence only outside the repository | preserve at copy-back (Log #98); independent check (Log #118) | procedure |
| R56 | Copy-back branch never tested at real path lengths; R2's copy-back stopped | allocator_digest.preserve | R2's real copy-back failed | failure in use | R2 copy-back interrupted; no data lost | long-path-safe copy, hash-verified --resume (Log #116) | test |
| R60 | Clean-up plan's list of writers into run folders was incomplete | docs/CLEANUP_PLAN.md | grepping every write call in src/ | agent itself | near miss | one guard helper; grep test for writers | test |
| R65 | New entry script wrote without the frozen-run guard | src/14_write_analysis.py | fast-suite test of writers | test suite | none | writes go through guard_write | test |

**Hand-off and state errors**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R7 | §0 claimed resumability but recorded no deadline | PROJECT_SPEC.md §0 | git grep over all revisions | agent itself | owner's deadline update had nothing to update | §0 Timeline (Log #45) | none |
| R27 | Owner decisions sent in a message that never reached the assistant were re-asked as open | chat | owner noticed repeated questions | owner | settled items listed as open | every owner decision written to §11 in the same session | procedure |
| R39 | Copy-back built the CHECKER matching before the extraction, against the planned order | copy_back / run_report | reading the report structure after copy-back | agent itself | container sizes seen; no values | noted; extraction isolated from those fields | none |
| R41 | Extraction requested as a 'new session' in a session that had read barred files | R1 extraction | checked before reading any input | agent itself | extraction deferred to a fresh session | none | none |
| R47 | Extraction comparison run before two parked rubric questions were closed | comparison_7a.json (fc29023) | owner | owner | resolution not blind; no claim moved | decisions applied side by side (§11 #61) | none |
| R62 | Interrupted session left uncommitted, unlogged work on a branch | branch cleanup | git status at the next session start | agent itself | none | stashed, reviewed, finished (Log #127) | none |

**Presentation and reporting errors**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R8, R9, R16 | Stale status line, an uncorrected Shock 3 rationale and a stale header in the docs | EVALUATION_PLAN.md, PROJECT_SPEC.md §10.2, AGENTS.md | reading the docs when resuming from the repository | agent itself | readers could trust stale text | fixed directly | none |
| R24 | Unverified cause stated as fact; milestone status overstated | R22, commit 317160d | owner asked for the full report | owner | misleading status | corrected | none |
| R30 | Pooled CHECKER recall reported as the headline | DRY1 report | owner's review | owner | would hide the headline types | stratified reporting (§11 #37) | procedure |
| R43 | Commit message stated a claim count the commit did not contain | commit f8357a5 | encoding output checked against the spec | agent itself | false record in history | counts taken from the encoder | none |
| R44 | Count in the session log written from memory | docs/SESSION_LOG.md | check against the file | agent itself | none | corrected (2eea94f) | none |
| R48 | Report opened with a blanket completion claim its body contradicted | session report | owner | owner | misleading status | status item by item | none |
| R49 | Computed values written into a draft before being looked up | session log draft | re-read before appending | agent itself | none | values from the file | none |
| R57 | A count in a report attached to the wrong set | report on fc5a944 | owner's review | owner | self-contradictory report | re-hashed and reported separately | none |
| R63 | Numbers typed by hand into the ANALYSIS.md prose | analysis template | reading the render; then a test | agent itself | numbers outside HEADLINE_NUMBERS.csv | references by id; test for typed numbers | test |
| R64 | An empty matching stratum hid the CHECKER's only shock-day issue | src/13_stress1.py | stop rule for exact-zero strata | agent itself | near miss | LLM-only issues per stratum | none |
| R67 | Level and tier rows side by side made A4 look like a broken floor | ANALYSIS.md §1.4 | owner reading ANALYSIS.md | owner | a correct result read as a bug | tier rows; identity stop check | test |
| R69 | Hidden series in F3/F4 and invisible zero floors in F1/F2 | results/figures/ | opening every PNG | visual inspection | near miss | layered lines, floors in tick labels, shared scale | none |
| R70 | A stale 'pending' claim survived a merge in the README | README.md | editing the same row | agent itself | stale claim on main | row rewritten | none |
| R71 | Wrong anchor links, a duplicate register id, a wrong caption file name and typed numbers in the first ERROR_ANALYSIS render | error_analysis_template.md, error_register.csv | computed anchors; register test; reading part D; typed_numbers | agent itself | near miss: none reached main | anchors tested; id renamed; render takes the list name | test |

*Source: [`results/analysis/error_register.csv`](results/analysis/error_register.csv) (hand-curated from `docs/REFLECTION_LOG.md`, the id of each row), rendered by `src/16_error_analysis.py`.*

## C. Errors in the verification itself

*The reference is not a gold standard.* The owner's independent extraction differed from the assistant's on 43 [`ea_a2_adjud.discrepancies.count`] claims. By cause: owner encoding 28 [`ea_a2_adjud.owner_encoding.count`], owner miss 7 [`ea_a2_adjud.owner_miss.count`], rubric ambiguity 6 [`ea_a2_adjud.rubric_ambiguity.count`], matching rule 2 [`ea_a2_adjud.matching_rule.count`]; assistant miss 0 [`ea_a2_adjud.assistant_miss.count`], assistant encoding 0 [`ea_a2_adjud.assistant_encoding.count`] (R52: causes proposed by an LLM advisor and accepted by the owner). The rubric's strict reading of *spare*/*free* made 54 [`wrong_claims_sets.rubric_dependent_spare_free.size`] correct claims count as wrong (R42).

| | register rows |
| --- | --- |
| Owner-side discrepancies | 1 |
| Rubric gaps | 1 |
| Extraction errors | 1 |
| Specification gaps | 1 |
| Consultant, owner or record errors caught | 7 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_c.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*

**Owner-side discrepancies**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| owner-side discrepancies | 43 discrepancies between the owner's independent extraction and the assistant's, all attributed to the owner side or the rubric (see the counts table) | owner_adjudication_causes.csv | adjudication of every unmatched claim | owner | the owner's sample is not a gold standard | causes recorded; descriptive recall next to the primary | none |

**Rubric gaps**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R42 | Rubric had no rival reading for 'spare'/'free'; the ALLOCATOR used them for beds left empty | EVALUATION_PLAN.md §4 item 9 | during extraction, before encoding | agent itself | 54 claims wrong only under the strict reading | rival reading added (§11 #59) | procedure |

**Extraction errors**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| extraction errors | Two claims encoded as today's overflow referred to yesterday's (R1-D28-05, R1-D28-06) | explanation_claims_spec.json | owner review of the wrong claims | owner | 2 of the 75 pre-registered wrong claims are correct | owner verdict extraction_error | none |

**Specification gaps**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R10-R14 | Prose definitions that could not be computed: nurse violation, movable bed, forced reallocation, explanation quality, mean days in overflow | CLAUDE.md §10.G, EVALUATION_PLAN.md | writing the exact formulas | agent itself | metrics undefined until fixed | owner decisions §11 #16-#21 | none |

**Consultant, owner or record errors caught**

| id | what went wrong | where | how it was found | found by | consequence | fix | rule added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Advisor's rationale for Shock 3 was wrong in its mechanism | PROJECT_SPEC.md §10.2 | check against the data; 1,000-seed Monte Carlo | independent check | the shock forces no cut | pre-registered sweep; LIMITATIONS §2 | none |
| R51 | Owner instruction assumed a duplicate rule that had never been applied | comparison_7a.json | checked before applying | agent itself | none | rule applied to the rows named only (§11 #65) | none |
| §11 #67 | Owner's same-figure condition of §11 #66 excluded pairs it was not meant to | PROJECT_SPEC.md §11 #66 | owner | owner | descriptive recall changed | condition corrected (§11 #67) | none |
| Log #125 | Owner's draft cited PROJECT_SPEC §1, §3.7, §3.10 for sections that are in EVALUATION_PLAN.md | plan.md wording | checking the cited sections | agent itself | none | citation corrected | none |
| R67 (owner's hypothesis) | Owner's hypothesis that the A4 floor was lexicographic | ANALYSIS.md §1.4 | definition and code checked; identity with A2 | agent itself | none | level/tier scale explained | test |
| R66 | Brief's premise that the day-12 self-verification was a CHECKER miss | §11 #73 brief | searching the records for the phrase | agent itself | none | case reworded as transcript-only | none |
| R62 (first version) | Assistant's first R62 read the leftover files as a wrong hand-off, before the crash was known | docs/REFLECTION_LOG.md R62 | owner's account | owner | a wrong record for one round | R62 rewritten | none |

*Source: [`results/analysis/error_register.csv`](results/analysis/error_register.csv) (hand-curated from `docs/REFLECTION_LOG.md`, the id of each row), rendered by `src/16_error_analysis.py`.*

## D. How each error was found

Each row is a kind of error, with its unit; each cell counts the errors of that row found by that method.

| | unit | deterministic audit or recomputation | manual review | matching protocol | tests and guards | visual inspection | owner or consultant review | agent's own check | independent check or failure in use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| allocation decisions, R1-R3 | audit issues | 279 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| allocation decisions, STRESS1 | audit issues | 99 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| explanation claims, R1 | wrong claims | 75 | 19 | 0 | 0 | 0 | 0 | 0 | 0 |
| CHECKER: audit issues missed, R1-R3 | audit issues | 0 | 0 | 62 | 0 | 0 | 0 | 0 | 0 |
| CHECKER: reports without an audit match, R1-R3 | CHECKER issues | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 |
| CHECKER: wrong claims not contested, R1 | wrong claims | 0 | 0 | 68 | 0 | 0 | 0 | 0 | 0 |
| CHECKER: wrong disputes, R1 | contested correct claims | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| development (coding agent) | cases | 0 | 0 | 0 | 5 | 1 | 11 | 30 | 7 |
| verification: owner-side discrepancies | claims | 0 | 43 | 0 | 0 | 0 | 0 | 0 | 0 |
| verification: rubric-dependent readings | claims | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 0 |
| verification: extraction errors | claims | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| verification: specification gaps | REFLECTION_LOG entries | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| verification: consultant, owner or record errors | cases | 0 | 0 | 0 | 0 | 0 | 2 | 4 | 1 |

*Source: [`results/analysis/error_analysis.csv`](results/analysis/error_analysis.csv), written by `src/16_error_analysis.py`. Each cell's id is `ea_d.<row>.<column>` (row and column names with every run of other characters as `_`) in `results/analysis/ERROR_NUMBERS.csv`.*
