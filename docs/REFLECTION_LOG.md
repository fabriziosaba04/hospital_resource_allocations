# Reflection Log

A running record of things that went wrong, or nearly went wrong, during the project. It is source material for the final Reflection (`LIMITATIONS_AND_REFLECTION.md`) and for the Verification section of the report.

**Rule (owner, 2026-11-11):** add an entry **at the moment** something like this happens, not at the end of a session, and mention new entries in the session report. Errors by the AI assistant count as much as errors in the code or the design.

*Paths: entries written before 2026-11-23 cite the layout before the repository clean-up. The development runs, fixtures, HARD10 figures and pre-run verification files have moved (mapping: `docs/CLEANUP_PLAN.md` §2.2); the agent runs and baselines have not.*

Each entry records:

- **What happened:** the error or near miss, stated plainly.
- **How it was caught:** which independent check revealed it.
- **Implication for AI-agent reliability:** what it teaches about trusting AI-generated reasoning, code or claims.
- **Decisions Log:** the related entries in `PROJECT_SPEC.md` §9.

---

## 2026-11-11

### R1. The rationale for Shock 3 was wrong (advisor error)

- **What happened:** the approved rationale for Shock 3 (beds −10 on days 23–25) was that it "hits while census is high, so relaxed no-eviction is exercised". The reasoning compared the census with the shocked pool. But a forced cut depends on the patients **carried over** from the previous day against the new pool, because new arrivals can always overflow instead. On the primary seed, only 62 patients carry over into day 23, against a pool of 86, so no cut is ever forced.
- **How it was caught:** an explicit check of the shock's stated purpose against the generated data (carried-over patients on each pool-decrease day), confirmed by the 1,000-seed Monte Carlo: P(forced cut) = 0.002 for the approved schedule. A pre-registered sweep of candidate schedules then selected nothing (best eligible: 0.52), and the threshold was **not** lowered after the fact.
- **Implication:** a plausible, approved rationale can be wrong in its mechanism. A design goal stated in prose ("this shock exercises X") must be verified quantitatively against the data. Pre-registering the selection rule kept the follow-up decision honest when the result was negative.
- **Decisions Log:** #33, #40, #41; owner decisions §11 #10–12; `LIMITATIONS_AND_REFLECTION.md` §2.

### R2. The floating-point example in Log #29 was wrong

- **What happened:** Log #29 justified exact integer arithmetic for the N1 requirement with the claim that `0.35 × 20` gives `7.000000000000001` in floating point. It does not: the result is exactly `7.0`. The underlying risk is real, but rarer than implied: 10 of the 68,921 census combinations up to 40 per level round wrong, for example (12, 0, 1): `0.2·12 + 0.6·1 = 3.0000000000000004`, so `ceil` gives 4 instead of 3.
- **How it was caught:** while writing the hand-computed N1 test, the assistant evaluated the claimed example directly. An exhaustive search then found the real failing cases.
- **Implication:** an AI assistant can state a specific technical "fact" with confidence that it has never checked. A correct decision (exact arithmetic) can rest on a false justification. Every concrete numerical claim in documentation should be executable or tested.
- **Decisions Log:** #29 (corrected), #42.

### R3. A property-test failure was a bug in the test, not in the validator

- **What happened:** the property test for `SHOCK_OVERCUT` failed. The test's mutation moved a bed into a department that had itself been cut. That only shifts the cut between departments, so the total cut does not grow and the validator was right to accept it.
- **How it was caught:** Hypothesis produced a minimal counterexample, and the assistant analysed it before changing any code. Only the test was changed.
- **Implication:** a failing test is evidence, not a verdict. An AI assistant asked to "make the tests pass" could just as easily weaken the validator. Every fix must say which side was wrong, and why.
- **Decisions Log:** #37 (environment cut path).

### R4. The validator did not compute the nurse requirement at all

- **What happened:** the owner asked for confirmation that the data validator computes the N1 requirement with its own integer implementation, separate from the generator's. In fact neither does: N1 is not stored in the datasets, so no data check uses it. It is computed in `stats.py` (descriptive statistics) and `src/environment/nurses.py`. The assistant reported this instead of confirming the assumption.
- **How it was caught:** the assistant read the code before answering.
- **Implication:** a request to "confirm" invites agreement. Both people and AI assistants should answer from the artefact, not from the premise of the question. A third, independent N1 implementation is still needed in the deterministic audit.
- **Decisions Log:** #37, #42.

### R5. Gaps in the run-session deny list

- **What happened:** hidden generation information stayed reachable until it was closed:
  - Monte Carlo outputs in `data/processed/montecarlo/` (before deny-by-default on `data/**`).
  - `tests/`, which contains the shock schedule and parameter values.
  - The `.hypothesis/` cache, which collects literals from source files.
- **How it was caught:** a real headless Claude Code session started with `.claude/run-settings.json`, whose tool results were classified from the transcript (`tests/manual/verify_run_settings.py`). A repository-wide `Grep` revealed the `tests/` and `.hypothesis/` paths. After the fixes, 16 protected reads were denied and the controls allowed.
- **Implication:** information hiding by deny-list is fragile, because new files keep appearing in unexpected places (caches, tests, analysis outputs). Deny-by-default plus an empirical check in a real session is much stronger than reasoning about paths. The dispatcher having no file tools remains the first layer.
- **Decisions Log:** #39; owner decisions §11 #8, #9, #13; `PROJECT_SPEC.md` §8.

### R6. Shock 1 is weak on the primary seed

- **What happened:** with nurse pool 33 on days 8–10, the N1 requirement on the primary seed is 36 / 33 / 34, so the shortage is only 3 / 0 / 1, while the census is low (79 / 77 / 76). There is no shortage on day 9, and no slack either.
- **How it was caught:** a per-day check of requirement against pool, requested by the owner before the freeze.
- **Implication:** Shock 1 must not be presented as a crisis in the report or in the ALLOCATOR's evaluation. Claims about what a scenario "tests" have to be checked on the actual dataset, not inferred from the parameters.
- **Decisions Log:** `PROJECT_SPEC.md` §0 (nurse checks); §10.2 (nurse-rationing regime).

## 2026-11-12

Entries R7–R16 are gaps found while resuming from the repository alone, at the owner's request ("treat each such gap as a REFLECTION_LOG entry"). **Status (later on 2026-11-12):** all are resolved. R7 by Log #45; R8 (the `EVALUATION_PLAN.md` status line), R9 (§10.2 annotated) and R16 (`AGENTS.md` header) fixed directly; R10–R14 by the owner's decisions §11 #16–#21 and Log #46–#52; R15 by §11 #22 (the stress run is planned and stays out of the main comparisons).

### R7. The deadline was not recorded anywhere

- **What happened:** the owner asked for every mention of "16 November" to be updated to the new internal deadline. No committed file, in any commit, mentions 16 November or any deadline date. §0 claimed to be "enough to resume from the repository alone", but it had no timeline.
- **How it was caught:** a search of the whole git history (`git grep` over all revisions) before editing anything.
- **Implication:** a handoff document can look complete and still leave out the constraint that drives planning. The owner's memory of what the docs say and what they actually say had drifted apart. An instruction that assumes text exists has to be checked against the file before it is carried out.
- **Decisions Log:** #45 (fixed: §0 Timeline added).

### R8. EVALUATION_PLAN status line is stale

- **What happened:** `EVALUATION_PLAN.md` says the formulas are provisional "until the first data generation". The data have been generated and frozen (`data-v1.0`), but the formulas are still provisional. What actually ends that status is the owner's decision on the metric proposal (§0 step 1).
- **How it was caught:** reading the status line against §0 and the git tag.
- **Implication:** a conditional status ("until X") goes stale silently once X happens. Status lines should name the decision that closes them, not an event.
- **Decisions Log:** §0 step 1.

### R9. PROJECT_SPEC §10.2 still states the wrong Shock 3 rationale

- **What happened:** the approved parameter table still says Shock 3 "hits while census is high, so relaxed no-eviction is exercised". R1 and Log #40 showed that this is false (P(forced cut) = 0.002), but the table has no annotation. A reader of §10 alone gets the false claim.
- **How it was caught:** reading §10.2 next to R1 and `LIMITATIONS_AND_REFLECTION.md` §2.
- **Implication:** correcting an error in one place does not remove it from others. Each correction should search for every place the false claim appears.
- **Decisions Log:** #33, #40; R1.

### R10. The nurse clinical violation has no unit, pairing rule or integrality treatment

- **What happened:** `CLAUDE.md` §10.G defines a nurse violation as "higher-level patients in d uncovered while lower-level patients are covered elsewhere". It does not say what is counted: patients, nurses or need units. It has no pairing rule (beds have one, in `EVALUATION_PLAN.md` §3.1), and it ignores the fact that need is fractional while nurses are whole. One nurse moved can uncover parts of two levels. As written, the audit cannot be implemented deterministically.
- **How it was caught:** trying to write the exact formula for the metric proposal.
- **Implication:** a definition that reads clearly in prose can still be impossible to compute. Every metric needs an executable definition before it is fixed.
- **Decisions Log:** §0 step 1(a).

### R11. "Movable bed" and how empty beds enter the pairing rule are not defined in record terms

- **What happened:** §10.G says a movable bed is "free, or freed by that day's discharges", but nothing defines it from the records. The bed pairing rule (`EVALUATION_PLAN.md` §3.1) pairs each unserved patient with "the lowest-level movable bed served in their place", but does not say whether empty beds count in the same pool, or where they rank. These choices change the counts and the severities.
- **How it was caught:** while writing the formula. The proposal treats a movable bed as one of the `B_d(t) − O_d(t)` beds not protected by no-eviction, and an empty bed as level 0. Under that reading, a random check (20,000 cases) found greedy pairing equal to the sum of the per-tier gaps.
- **Implication:** the same as R10. Ambiguities in prose surface only when someone has to write the code.
- **Decisions Log:** §0 step 1(a); owner decision §11 #3.

### R12. "Beyond what the pool change forces" has no reference allocation

- **What happened:** reallocation frequency (`EVALUATION_PLAN.md` §3.5) counts days on which the allocation changes "beyond what the pool change forces", but it does not say which allocation counts as forced. A pool change can be absorbed in many ways. The reversal window is listed as open, but this part is not.
- **How it was caught:** while writing the stability formulas.
- **Implication:** a metric that compares against a counterfactual must name that counterfactual.
- **Decisions Log:** §0 step 1(a).

### R13. The explanation-quality metric cannot be computed from the explanation fields

- **What happened:** `EVALUATION_PLAN.md` §3.7 measures "the share of decisions whose stated expected consequences match the deterministic outcomes". The `explanation` argument of `submit_decision` (`PROJECT_SPEC.md` §2.2) has six text fields and no structured prediction. A deterministic comparison is therefore impossible, and the metric would depend on an LLM reading the text.
- **How it was caught:** checking the metric against the tool signature.
- **Implication:** a metric and the record it reads have to be designed together. Otherwise the metric quietly becomes LLM-dependent, which the verification principle (`CLAUDE.md` §7) rules out.
- **Decisions Log:** §0 step 1(a).

### R14. "Mean days in overflow" is not what its formula computes

- **What happened:** the F2 metric "mean days in overflow" divides total overflow patient-days by **all** distinct level-k patients present, including those never in overflow. That is overflow days per patient, which is just the total overflow rescaled. It is not the mean time spent waiting by those who waited, and on its own it carries no fairness information.
- **How it was caught:** checking each formula's units and denominator for the proposal.
- **Implication:** a metric's name can promise more than its formula delivers.
- **Decisions Log:** §0 step 1(a).

### R15. The status of the stress run is unclear after the schedule change

- **What happened:** `EVALUATION_PLAN.md` §5 and §0 step 5 call the stress-variant run "optional". The owner's 2026-11-12 instruction reserves the extra time for "the stress scenario". It is not recorded whether the run is now planned, and whether it is still excluded from the main comparisons (owner decision §11 #12).
- **How it was caught:** comparing the new instruction with the run plan while updating §0.
- **Implication:** a change of plan can silently change the status of earlier decisions. The status has to be restated explicitly.
- **Decisions Log:** #41, #45; owner decision §11 #12.

### R16. AGENTS.md header date is stale

- **What happened:** `AGENTS.md` says "the design decisions were last updated on 2026-11-07", but §2.3 contains the 2026-11-11 deny-by-default rule.
- **How it was caught:** reading the header against the body.
- **Implication:** a minor issue, but "last updated" lines that are not maintained make readers trust stale text.
- **Decisions Log:** owner decision §11 #9.

### R17. The A2 closed form was wrong when nurses are scarcer than whole units of need (assistant error)

- **What happened:** the metric proposal of 2026-11-12 gave the tier maximum of nurse coverage as "if P_N ≥ Σ⌈a⌉ then Σa, else give each department ⌊a_d⌋ and the remaining nurses to the largest fractional parts". That silently assumes P_N ≥ Σ⌊a_d⌋. When P_N < Σ⌊a_d⌋ every nurse covers a full unit and the maximum is simply P_N; the stated formula overstates it (example: a = (2.4, 3.6, 1.2, 0), P_N = 4 gives 6 instead of 4). The case is not exotic: it occurs at tier 1 on rationing days. The assistant had the three-case form in its working notes but wrote only two cases into the proposal, and also claimed the closed form would be "cross-checked against brute force" while no such check had yet been run.
- **How it was caught:** the owner's review of the proposal, before any code was written. Confirmed by brute force on the example.
- **Implication:** a proposal that promises a verification ("cross-checked against brute force") reads as if the check were done. Formulas offered for a fixed, pre-registered evaluation must be executed before they are proposed, not after approval.
- **Decisions Log:** #46.

### R18. A hand-computed test expectation was wrong (assistant error)

- **What happened:** the new initial-allocation test expected the spare nurse to go to Neurology. The quotas were 12.33, 10.28, 6.17 and 8.22, so the largest fractional part is Internal Medicine's (0.33), and the code was right. The assistant had written the fractions correctly in the comment and still mis-ranked them.
- **How it was caught:** the test failed on its first run. The assistant recomputed the quotas before touching any code, and changed only the test.
- **Implication:** as in R3, a failing test is evidence, not a verdict. Hand-computed expectations are themselves claims that need checking; writing the intermediate numbers into the test made the error easy to locate.
- **Decisions Log:** – (`tests/test_environment_rest.py`).

### R19. A headline metric could reward leaving empty beds alone (gap in the assistant's proposal)

- **What happened:** the metric proposal flagged that B0 "wins stability trivially", and bed reversals within W were approved as a headline metric. The baseline runs show that B1 and B2 reverse 103–116 bed units within W = 3, and that 45–78% of the bed units they move land on beds that are idle that day: both rules re-split spare beds by census every day. The reversal count therefore mostly measures churn of empty beds. An agent that leaves spare beds in place would score far better than B1 and B2 on a headline metric without allocating any better. The proposal did not flag this, although the owner had asked for every metric where an agent could look good without allocating well.
- **How it was caught:** the headroom review the owner required before confirming the headline set (`EVALUATION_PLAN.md` §8), followed by a direct count of moved bed units landing on idle beds.
- **Implication:** whether a metric can be gamed is often visible only against real policy outputs. Requiring a baseline-only headroom review before fixing the headline set caught it without anyone seeing agent output.
- **Decisions Log:** owner decision §11 #18; `EVALUATION_PLAN.md` §8.4 finding 4. **Resolved 2026-11-12 as a validity fix, not a result-driven change** (owner decision §11 #26): under no-eviction, moving beds has no real cost in the model, so stability is demoted to secondary and reported as two counts, all reversals and reversals of beds occupied in between (Log #59). The decision rests on baseline outputs only.

### R20. Baseline records reopen a second-layer leak path in run sessions

- **What happened:** the baseline records committed to `results/` contain each patient's bed status on every day of the horizon. That reveals future arrivals and, implicitly, discharge days. `.claude/run-settings.json` denies `Edit(./results/**)` but not `Read(./results/**)`. The first layer still holds, because the dispatcher has no file tools and the subagents have only their MCP tools. But the deny-list layer no longer covers all future information, the same failure pattern as R5.
- **How it was caught:** the assistant checked the deny rules against the new files before committing them.
- **Implication:** every new output directory is a potential leak path. The deny list has to be re-checked whenever a step writes new files, not only when data files change.
- **Decisions Log:** owner decisions §11 #9, #13; `PROJECT_SPEC.md` §8. **Resolved 2026-11-12** (owner decision §11 #27): `Read(./results/**)` added to the run settings, `verify_run_settings.py` extended with `results/` probes and re-run (Log #60).

### R21. Tool errors would have reached the agents without their message

- **What happened:** in the MCP SDK (v2), an exception raised inside a tool reaches the model only as "Error executing tool <name>"; its own text stays on the server. The state machine's rejections carry the expected next action ("… Expected next action: call end_allocation_phase"), and the validator's reasons come back the same way. As first written, the ALLOCATOR and the dispatcher would have seen only the generic text, and could not have corrected a wrong-phase call or a schema error. The workflow unit tests passed, because they call the Python methods directly.
- **How it was caught:** a raw JSON-RPC exchange with the stdio server before the smoke test, which showed the generic error text for a call with no active run.
- **Implication:** tests that bypass a transport layer cannot see what that layer does to messages. At least one check has to go through the real protocol before an LLM depends on it.
- **Decisions Log:** #62.

### R22. The smoke test ran the draft prompts end to end, because the dispatcher refused the smoke instructions (assistant design error)

- **What happened:** the smoke-test design assumed the dispatcher would follow a one-off user prompt replacing its loop with mechanical steps: subagents calling their own tools without judgement, trying foreign tools, and a test spawn of an `Explore` subagent. The dispatcher refused. It answered that its protocol allows only the fixed workflow steps and the two fixed prompts, and ran its **normal loop**. The ALLOCATOR and CHECKER, with the **draft prompts the owner has not yet reviewed**, therefore made real decisions for 5 days and wrote a validation report. This happened on the synthetic SMOKE5 fixture with haiku; no frozen dataset was touched. But it is not what the owner asked for ("draft the prompts for my review; don't run any agent session"). A first attempt had stopped after one call. *Corrected 2026-11-12 (R24):* the reason for that stop is **unknown**, because that run's transcript and final text were not saved. "For the same reason" was an inference stated as fact.
- **How it was caught:** the smoke script classifies the transcript and keeps the dispatcher's final text, which states the refusal. Every call the dispatcher made was a workflow tool or one of the two fixed templates, word for word.
- **Implication:** the refusal is itself good evidence for dispatcher neutrality: a system prompt that forbids improvising held against a direct user instruction. But a test that needs an agent to step outside its role cannot be run through that agent. The assistant should have predicted this from the dispatcher prompt it had just written. Check 5c (the dispatcher cannot spawn other subagents) could not be shown live, because the dispatcher never tried.
- **Decisions Log:** #69, #70.

### R23. The occupied-reversal count is not monotone in the window W

- **What happened:** with a wider window, all reversals grow as expected, for example B1 on seed 07: 100 / 116 / 126 for W = 2 / 3 / 5. The occupied-in-between count does not: B1 on seed 08 gives 28 / 36 / 26, and on seed 09 7 / 6 / 10. The oldest-first matching pairs different units when W changes, and the occupied lower bound depends on which units are paired. The count therefore partly reflects the matching procedure, not only the allocation. The assistant reported the W = 3 values without looking at the sensitivity columns.
- **How it was caught:** reading the W = 2 / 3 / 5 columns of the baseline metrics while preparing the owner's report.
- **Resolved (owner decision §11 #32):** the count was dropped before any agent output.
- **Implication:** a pre-registered sensitivity check is useful only if someone reads it. A metric built on a greedy matching needs a property check (monotone in W) before it is relied on. The definition (Log #59) is still awaiting owner confirmation, so nothing has been fixed yet.
- **Decisions Log:** #59.

### R24. Unverified cause stated as fact in R22, and milestone status overstated (assistant error)

- **What happened:** (1) R22 said the first smoke run stopped "for the same reason" as the second, but that run's transcript was never saved, so the cause is unknown. (2) Commit `317160d` labelled the MCP work "milestone 2" in `PROJECT_SPEC.md` §0, although the milestone is "smoke test passing" and one check (5c) failed. The commit also includes `results/evaluations/smoke_test.json` with `passed: false`. (3) The assistant's report ended with a test list that the owner read as the whole report.
- **How it was caught:** the owner asked for the full report and for any failing check committed; the assistant re-read R22 and the commit while answering.
- **Implication:** status words ("built", "milestone") must match the stated criterion exactly, and causes must be marked as inferred when they are.
- **Decisions Log:** #70.

### R25. The approved design gave both agents the evaluation's answers

- **What happened:** the agent design approved on 2026-11-07 had the CHECKER read the deterministic audit, through `get_deterministic_audit` (Log #6), and had the ALLOCATOR's what-if return clinical-priority violations (`AGENTS.md` §5, `PROJECT_SPEC.md` §2.2, §5.6). The owner and the advisor (the assistant) both approved it. The CHECKER prompt even told it to "report every issue in the deterministic audit that you can confirm". The CHECKER-versus-audit matching, a primary Verification output, would then have measured copying, not checking. A1, the "does the agent match B1" test after the headroom result, would have measured whether the agent searched proposals until the tool's violation count was 0, not whether it reasoned. The assistant also returned the nurse tier gaps (the A2 headline) from the what-if; the owner removed those too.
- **How it was caught:** the owner's review of the two prompts, before any run on frozen data. The assistant had written both the server and the prompts and did not see it.
- **Implication:** an evaluation is only valid if the evaluated agent cannot see the evaluator's answer key. Exposing a metric through a tool is a quiet form of leakage. It passed every information-rule test, because those tests checked for *future* information, not for *evaluation* information. Visibility reviews should ask "could the agent read off its score?", not only "could it see the future?".
- **Decisions Log:** #6 (superseded), #71–#74; owner decision §11 #29.

### R26. A new test nearly passed while checking less than it claimed

- **What happened:** the first version of the taxonomy-coverage test extracted the audit's issue types from source code with a regular expression. The regex missed `nurse_gap` (a multi-line call) and `f1_inversion` (its character class excluded digits). The test passed, but it was checking only 6 of the 11 types.
- **How it was caught:** the assistant printed the extracted set before relying on the test. The test now lists the 11 types explicitly and asserts that each one still appears in the audit source.
- **Implication:** a passing test proves only what it actually exercises. A test whose expected set is computed should show that set at least once.
- **Decisions Log:** #74.

### R27. Owner decisions that never reached the assistant

- **What happened:** the owner's message of 2026-11-12 said the model choice, the reversal-metric decision and the pre-R1 robustness items "were already decided in an earlier message that apparently didn't reach you". The assistant's report had listed them as open questions. Nothing in the repository recorded those decisions, so the assistant could not have known them.
- **How it was caught:** the owner noticed that the open-question list repeated items already settled.
- **Implication:** decisions that live only in chat are as fragile as conversational memory, which the project already forbids for agents (`CLAUDE.md` §10.J). Every owner decision is now written into `PROJECT_SPEC.md` §11 in the same session, so the repository stays the only source of truth.
- **Decisions Log:** owner decisions §11 #31–#35.

### R28. The reversal definition asks the CHECKER for a computation it cannot do, and the dry run shows it (assistant design gap)

- **What happened:** to match the audit exactly (owner decision §11 #35), `checker.md` defines reversals against the *reference allocation*: the previous allocation adjusted to pool changes by the largest-remainder repair rule. In the dry run, the CHECKER found every reversed move, but it wrote that "the day-4 bed reversal depends on a reference allocation I could not compute exactly" (the fixture's pool changes on days 3 and 4). It also merged the two departments of each round trip into a single issue, although the definition counts one issue per department and day. Result: recall 0.43 (3 of 7), with precision and level agreement 1.0. Every miss is a counting-unit or reference-rule difference, not a missed detection.
- **How it was caught:** the deterministic CHECKER-versus-audit matching in the dry-run report, then reading the report's own text.
- **Implication:** a definition can match the audit word for word and still be unusable by the agent who must apply it. Definitional alignment needs two halves: the same words, and the same means of computing them (here the reference allocation, which the CHECKER cannot see). Matching scores on reversals would otherwise measure arithmetic, not checking. Owner decision pending.
- **Decisions Log:** #84; owner decision §11 #35.

### R29. The synthetic fixture never exercises clinical-priority detection

- **What happened:** in the dry run, the deterministic audit found no bed pairs, no nurse gaps, no F1 inversions and no rejected submissions on any of the 5 days. The fixture is small (mean census 20.6 against 87.8 in the primary dataset), and its only pool changes are mild. The dry run therefore tested the plumbing, the ALLOCATOR's process and the CHECKER's reversal and explanation checks, but **not** whether the CHECKER can find clinical-priority violations, which carry the headline metrics.
- **How it was caught:** the per-day issue table in the dry-run report.
- **Implication:** a dry run proves only what its data make happen. A fixture meant to test detection must contain the cases to be detected. A harder synthetic fixture (more pressure, a forced cut) is the obvious remedy; it stays within the prompt development rule (§11 #34), because it is synthetic.
- **Decisions Log:** —.

### R30. Pooled CHECKER recall was reported as the headline (assistant reporting error)

- **What happened:** the DRY1 report led with pooled CHECKER-versus-audit figures (recall 0.43, precision 1.0). All 7 audit issues were Minor reversals. A pooled figure weights every issue equally, so on a real run, where reversals are numerous, it would mostly measure reversal bookkeeping. It would hide how the CHECKER does on the clinical and hard-constraint types that carry the headline metrics.
- **How it was caught:** the owner's review of DRY1 (2026-11-14).
- **Implication:** an aggregate over heterogeneous issue types inherits the mix of the most frequent type. Verification figures must be stratified by type, by severity, and by the group the evaluation cares about.
- **Decisions Log:** owner decision §11 #37; Log #86.

### R31. The forced cut in the hard fixture cannot be guaranteed independently of the policy

- **What happened:** the hard fixture was meant to "guarantee a forced shock cut". Whether holders outnumber the pool on day 8 depends on how many beds were filled on day 7, which is an allocation outcome. Under B0, which leaves beds idle in departments without waiting patients, day 8 is never a shock day, even with the bed pool cut from 20 to 11. The first draft of the fixture also gave only empty-bed pairs, with no L3-vs-L1 or L2-vs-L1 displaced pair.
- **How it was caught:** probing the draft fixture under B0–B2 before writing the test.
- **Implication:** a fixture can guarantee data conditions, not decisions. The test therefore states the cut guarantee as a bound: any allocation that fills every bed on day 7 leaves 13 holders for 11 beds. It also shows the shock day under B1 and B2. If the ALLOCATOR leaves beds idle on day 7, DRY2 may not exercise the cut, and the report must say so. *Outcome (DRY2):* the cut was exercised (20 beds filled on day 7, 3 beds cut on day 8). But the ALLOCATOR avoided every bed conflict the fixture offered, so the CHECKER's bed-violation detection is still untested on positives; this is an open question for the owner.
- **Decisions Log:** #88.

### R32. The CHECKER's two "late-dated" bed reversals reused units already matched

- **What happened:** in DRY2 the audit has two bed reversals on day 6: internal medicine (τ +2 undoing part of day 4's −3) and neurology (τ −1 undoing day 5's +1). The CHECKER missed both and instead reported neurology on day 7 ("+1 undid the day 6 tau of −1") and internal medicine on day 8 ("−1 undid 1 of the +2 beds given on day 6"). The τ values it quotes are correct. What it got wrong is the matching rule: each unit is matched once, oldest first, so day 6's units had already been used to reverse days 4 and 5, and days 7 and 8 are new moves, not reversals. The cause is **matching against the most recent opposite move**, not dating from occupancy trends (the owner's hypothesis, which these two items do not support).
- **How it was caught:** reading the two items against the audit's per-day τ (owner request, 2026-11-14).
- **Implication:** the date-shift count (§11 #45) catches both items, but its name suggests a dating error. The report must state the cause, not just the count. The prompt is not changed (owner decision §11 #45).
- **Decisions Log:** owner decisions §11 #45, #46.

### R33. Reversal recall is a reading test, and the matching figures rest on small counts

- **What happened:** after §11 #36 the CHECKER receives the reference allocation and τ, computed exactly as in the audit. DRY2's secondary-group figure (9/11) therefore measures how well it reads τ and applies the matching rule, not whether it detects reversals independently. Separately, the headline result of DRY2 is 4/4, all one type (`nurse_gap`), and a rate of "1.0" would hide both the small count and the single type.
- **How it was caught:** the owner's review of DRY2 (2026-11-14).
- **Implication:** giving an agent an input changes what the matching measures. Every exposed intermediate should be listed next to the figures that depend on it, and small counts are reported as counts.
- **Decisions Log:** owner decisions §11 #46, #47.

### R34. The synced-folder guard first allowed frozen data whenever the manifest could not be read

- **What happened:** the launcher's guard accepts `--allow-synced-folder` only for synthetic fixtures. It decides "frozen" by looking the dataset up in `data/MANIFEST.json`. The first version returned "not frozen" when the manifest file was missing, so a missing or unreadable manifest would have let a frozen-data run start inside OneDrive with the flag.
- **How it was caught:** the guard's unit test, which moves the project root to a temporary folder, failed with "DID NOT RAISE".
- **Implication:** a safety check must fail closed. When it cannot decide, it now treats the dataset as frozen and refuses. The test also exposed that the manifest path depended on a patched global; it is now fixed at import time.
- **Decisions Log:** #90.

### R35. "B1 is near-optimal on nurses" was a premise, and a synthetic fixture falsified it first

- **What happened:** after the headroom review the evaluation was framed as "can the agent reproduce a near-optimal myopic policy (B1)?" (owner decision §11 #24). On A2 that rested on small B1 gaps on the frozen seeds, but nobody had stated where B1's nurse rule stops being near-optimal. On HARD10, DRY2 beat B1 at every A2 tier (tier 3: 0 against 1.2 need units), so the premise was false on that fixture.
- **How it was caught:** the baseline table on HARD10 the owner asked for (2026-11-14), then the recomputation of B1's gap per tier on the three frozen seeds.
- **Outcome:** on the frozen seeds B1 is optimal at tier 3 and within 0.22% of tier-2 need, so the framing holds there with a measured gap. But it is a measured property of these data, not a property of B1. B1 rounds up to whole nurses per department, which costs more when departments are small.
- **Implication:** a framing word like "near-optimal" is a claim and needs a number and a scope. The fixture built to test the CHECKER also tested the framing, before any agent output on frozen data.
- **Decisions Log:** owner decision §11 #50.

### R36. The run report would have shifted every day after a usage-limit cutoff

- **What happened:** the run report attributed each subagent invocation to a day by counting successful `advance_day` results across all launch transcripts. If a session is cut off after the server applies `advance_day` but before the result reaches the transcript, which is plausible for a usage-limit cutoff, every later day's tokens, tool calls and timings would be credited to the previous day. Launches were also sorted as text, so `launch-10` would come before `launch-2`.
- **How it was caught:** checking the resume path for usage cutoffs (owner's note on cost, 2026-11-14) by reading `transcript_stats`.
- **Fix:** each invocation takes the day reported by the last orchestration tool result before it, and launches sort numerically (Log #92). A synthetic two-launch transcript test covers both.
- **Implication:** the resume tests proved that the records survive an interruption, but not that the *reports* do. Every derived output needs its own interruption check.
- **Decisions Log:** #92.

### R37. In a fresh clone the role servers did not start, and the launch still reported success

- **What happened:** the first dry run launched from the clone outside OneDrive (`C:\hra-runs\…`, DRY3-RESUME on the synthetic SMOKE5 fixture) stopped on day 1. The Agent tool refused to spawn the ALLOCATOR: "would be spawned with zero tools … `mcp__allocator__*` matched no tools". The orchestration server, configured in `.mcp.json` and enabled by the run settings, connected. The allocator's inline server, defined in its agent frontmatter, did not, although the same server started and answered an MCP handshake when run by hand in the clone. The OneDrive folder has `hasTrustDialogAccepted: true` in the Claude Code configuration; the clone has no entry. **Inferred cause (not verified against documentation):** Claude Code does not start a subagent's inline MCP servers in a folder that has never been trusted. The dispatcher behaved correctly: it did not call `end_allocation_phase`, which would have applied the repair rule, and it stopped with an explanation. **But the launcher recorded exit 0 and "consistent"**, so the stalled run looked clean.
- **How it was caught:** the resume test in the clone, run before any R-run, on synthetic data.
- **Fix:** the launcher counts refused spawns and exits 1 unless the run is FINISHED (Log #94). The run procedure now requires opening the clone once with `claude` and accepting the trust prompt. Confirming the cause needs that step, then a relaunch.
- **Implication:** the clone procedure was tested for paths and copy-back, but not for Claude Code's per-folder state. The pre-R1 smoke test would have caught it (it checks that both role servers connect), which is why it is a condition of the tag. "Exit 0" must never stand for "the run finished".
- **Decisions Log:** #94.
- **Update 2026-11-15, cause confirmed by intervention.** The owner opened the clone once with `claude` and accepted the trust prompt; `~/.claude.json` then had `hasTrustDialogAccepted: true` for `C:/hra-runs/hospital_resource_allocations`. Nothing else was changed (same commit of code, prompts and settings; `verify_run_settings.py` in the clone gave the same 30 verdicts as the repository record, 21 denied, 0 leaks). The relaunch of DRY3-RESUME then spawned the ALLOCATOR with its tools and completed days 1–2. One change, one flip: the cause is confirmed by intervention, no longer only inferred. It is still not confirmed against documentation.

### R38. A day's wall clock counted the night between two launches, and a cut-off launch's cost disappeared

- **What happened:** the live two-launch test of DRY3-RESUME (synthetic SMOKE5) ran in three launches: launch 1 (2026-11-14, stalled by R37), launch 2 (killed on purpose mid-run, at day 3 READY_TO_CLOSE, to simulate a usage-limit cutoff) and launch 3 (finished). The records were consistent after the kill and at the end, and every subagent invocation landed on the right day (R36 fix confirmed live). But the rebuilt run report gave **day 1 a wall clock of 52,709 s** (14.6 h): it was computed as `close_day − advance_day`, and day 1 was advanced in launch 1 and closed in launch 2 the next morning. Day 3 included the minute between the kill and the relaunch. And `session_cost_usd` silently **left out launch 2**, because a killed session never emits its final cost event, so the run's cost would have been understated with no sign of it.
- **How it was caught:** reading the per-day report after the live copy-back (owner's Q2.3), not by a test: R36's synthetic test covered day attribution only.
- **Fix (Log #96):** a day's `wall_clock_s` is now the part of [advance_day, close_day] inside some launch (each launch's interval = first to last transcript timestamp); the raw span is kept as `elapsed_s`, with the number of launches the day touches. Every launch transcript is listed in `session_cost_usd`; a cut-off launch shows `null` (cost not reported), never a missing key. DRY2's report changes only by the two added fields.
- **Implication:** the same lesson as R36, one level further: the interruption check of a derived output must cover **every field** of it, timing and cost included, not only the one that prompted the check. For R1, a total cost is complete only if no launch shows `null`.
- **Decisions Log:** #96.

### R39. The R1 copy-back computed CHECKER-vs-audit matching, which the session had been told not to compute yet

- **What happened:** the post-R1 order says the copy-back rebuilds the run report and that CHECKER matching waits until the claim extraction (step 2) is committed. But `copy_back` calls `run_report.build`, and the run report **always** contains the CHECKER matching (`checker`, `checker_overall`: recall, precision, level agreement, per-type and per-level tables). So the rebuilt R1 report already holds the matching, computed by code, before the extraction. The two instructions were in conflict since the plan was written (SESSION_LOG, "copy_back copies everything … and rebuilds the report"); nobody had noticed because the dry runs had no extraction step. In addition, the assistant printed the report's key structure to find the cost and timing fields; that listing showed the **container sizes** of the CHECKER fields (6 period entries, which is expected, and a `date_shift_matches` list of length 4). No values of recall, precision, issue counts or report text were printed, and no CHECKER report was opened.
- **How it was caught:** by the assistant, reading the report structure right after the copy-back.
- **Outcome:** the matching numbers sit unread in `results/evaluations/R1/run_report.json`. The independence rule of `EVALUATION_PLAN.md` §4 item 7 concerns the **extraction session**: it must not read CHECKER reports, and now it must not read the CHECKER fields of `run_report.json` either. The one leaked quantity (4 date-shift matches) says nothing about the content of the ALLOCATOR's claims, which is what the extraction reads.
- **Implication:** a "do not compute X yet" ordering is only enforced if no automatic step computes X. For R2 and R3, either the extraction session's instructions must exclude `run_report.json`'s CHECKER fields, or the report must be built without them until the extraction is committed. Structure listings of a record that holds sequestered content are themselves a read.
- **Decisions Log:** none (no code change in this session).

### R40. "Copy-back takes everything the run wrote" left out the ALLOCATOR's own transcripts

- **What happened:** the run procedure and `copy_back` treat the run folder as everything the run wrote. But Claude Code writes each subagent's transcript, and any large tool result it spills to a file, to its own session folder (`~/.claude/projects/<clone>/<session>/subagents/`, `tool-results/`), not to the run folder. For R1 that is 30 ALLOCATOR and 6 CHECKER transcripts and 13 spilled ALLOCATOR tool results. The only copy in the repository was the dispatcher's stream transcript, which mixes every role and is barred for the extraction (§11 #58). The evidence for the copied/derived split (`EVALUATION_PLAN.md` §4 item 8, "the tool results the ALLOCATOR received") therefore existed only outside the repository, in a folder Claude Code may clean up after its retention period.
- **How it was caught:** by the assistant, while listing the files the extraction may read.
- **Fix:** `allocator_digest preserve` copied the 85 files into `results/allocations/R1/transcripts/subagents/`, split by `agentType` and hash-checked against the source (Log #98).
- **Implication:** "everything the run wrote" was tested against the run folder, not against everything the *harness* writes for the run. For R2 and R3, `preserve` must run at copy-back time, before the session folder can age out. Spilled results also matter for the rubric: the ALLOCATOR received a preview, not the file, so a value present only in the full file is not "received".
- **Decisions Log:** #98.

### R41. The extraction was requested as a new session, but this session had already read barred files

- **What happened:** the extraction prompt is headed "(new session)" and bars `run_report.json` and the deterministic audit as whole files (§11 #58). It arrived in the same conversation as the R1 copy-back, in which the assistant had already read from those files: R1's A1–A3 totals (computed from the audit), the audit issue counts by type (94 reversals, 5 nurse gaps, 2 reallocations without effect), day 1's full report entry (including one `reallocation_without_effect` issue), and the size of two CHECKER fields (R39). It had read no CHECKER report text and no ALLOCATOR explanation.
- **How it was caught:** by the assistant, before reading any extraction input.
- **Outcome:** the assistant did the preparation that does not depend on reading the explanations (access rule recorded, transcripts preserved, the filter and digest, a test) and **did not extract**. The extraction is left to a fresh session that has never seen the audit, the run report or the CHECKER output.
- **Implication:** an independence rule that bars files is about the *reader's context*, not only the files opened from now on. A prompt that says "new session" is a precondition to check, not a label.
- **Decisions Log:** none.

### R42. The rubric had no rival reading for "spare" and "free", and R1's ALLOCATOR uses both for beds left empty

- **What happened:** reading R1 days 1–3 for the claim extraction, the extractor found that the ALLOCATOR often writes "spare" or "free" beds for beds minus census (beds left empty after assignment), while rubric §4 item 2 reads both strictly as beds (or pool) minus occupied. Day 2: "IM holding 6 spare beds" (beds − census 6, beds − occupied 13), "about 13 free beds" (96 − 83 = 13, pool − occupied 31). Day 3 uses both senses in one sentence: "2 spare beds, 6 spare above occupied". Item 9 listed a rival reading only for *empty* (→ spare), so every such claim would have counted as an arithmetic error, not a rubric-dependent one.
- **How it was caught:** during extraction, before any claim was encoded or recomputed; escalated to the owner rather than encoded case by case.
- **Fix:** owner decision §11 #59: strict reading stays primary and is the only one in the headline count; rival reading *empty* (`empty_beds`) on every spare/free claim, uniformly. Added under item 9's rule (before the extraction commit), but **after the extractor had read three days of R1**, which is stated wherever rubric dependence is reported.
- **Implication:** the DRY2 calibration did not exercise this wording (its one spare/empty case went the other way, D7-58). A rubric fixed on one run's language can miss the next run's; the rubric-dependent count is the safeguard, and it works only if the rival list covers the terms actually used.
- **Follow-up (days 4–5):** the ALLOCATOR also writes "spare beds above census" and "spare above occupied". Under the uniform rule an exactly right "above census" figure would have counted as wrong in the headline. Escalated again; owner: an explicit qualifier sets the reading (above census → `empty_beds`, above occupied → `spare_beds`), bare terms keep strict + rival.
- **Decisions Log:** §11 #59.

### R43. A batch commit message stated a claim count that the commit did not contain

- **What happened:** during the R1 extraction, one shell call chained a viewer edit, the append of day 20's claims to `days_16_20.py`, the encoding run and the commit with `&&`. The viewer edit failed (a `sed` quoting error), so day 20 was never appended; the encoding run still printed four days and the commit went through with the message "batch 4 (days 16-20): 197 claims (686 total)". The commit `f8357a5` holds days 16–19 only: 148 claims, 637 in total.
- **How it was caught:** the encoding output listed days 16–19 and no day 20; checked against the spec (637 claims, last day 19) before going on.
- **Fix:** day 20 appended in a separate commit (`add_claims.py` now takes an optional day filter); commit counts are taken from the encoder's output, not written ahead of it. The wrong message on `f8357a5` stays in history and is corrected by the next commit's message and here.
- **Implication:** a commit message is a record. Writing its numbers before the command that produces them has run, and chaining unrelated steps so that one failure skips a later step silently, together produced a false record within one call.

### R44. A count in the session log was written from memory, not from the file

- **What happened:** the sixth-session entry's parked question said the non-strict comparisons ("worse", "more", "less") covered "9 claims". Counting them in `explanation_claims_spec.json` gave 7.
- **How it was caught:** checked against the file before the session report, as the verify-before-asserting rule requires; corrected in `2eea94f`.
- **Fix:** the count and the claim ids are now in the entry.
- **Implication:** the same pattern as R43, in a document instead of a commit message. Figures go into records only after the command that produces them has run.

### R45. A planned code change rested on an unchecked assumption about the what-if engine

- **What happened:** the sixth-session "Next" item asked to make `beds` / `nurses` independent of the allocation's validity, because "the in-effect allocations on shock days" would otherwise come out unverifiable. The README had hedged it ("if the engine returns no assignment"), but the session log stated it as a required fix.
- **How it was caught:** before changing the code, a probe over all R1 claims (2026-11-18) showed `simulate` drops the assignment only on BOUNDS / INTEGRALITY. The six shock-day in-effect allocations fail conservation only, so all 38 affected claims already returned figures; 0 were unverifiable for this reason.
- **Fix:** the change was made anyway as a defensive one (Log #100), and the probe result is recorded. No verdict changed.
- **Implication:** a hedged risk copied into a to-do list loses its hedge. Check the engine's behaviour before scheduling a fix for it.

### R46. A test assertion was written from memory of an earlier run, not from the current output

- **What happened:** `tests/test_owner_claims.py` asserted 19 non-mechanical mappings. That was the count before a fix moved the vague row 161 out of that list (rule U1 now applies first), and the current output has 18.
- **How it was caught:** the test failed on its first run (2026-11-18).
- **Fix:** the assertion now uses the current output (18), checked against `non_mechanical_mappings.csv`.
- **Implication:** the same pattern as R43 and R44. Here the test did its job, but the expected value has to come from the current artefact.

### R47. The extraction comparison was run before the owner's two parked rubric questions were resolved

- **Stub, created by the assistant at the owner's request (2026-11-18); the substance is the owner's to write.**
- **Facts recorded so far:** the item-7a comparison (`comparison_7a.json`, commit `fc29023`) was computed while two rubric questions were parked: patient attributes (item 1 vs the item-8 example) and the tier-2–3 requirement. The assistant's converter decided the second one provisionally (rule Q2, owner rows 115–118). The owner resolved both on 2026-11-18 (§11 #61 A–B) **after** the comparison had been seen, so the resolution is no longer blind to the recall figures. Applied side by side (`comparison_7a_decisions_AB.json`), neither decision moves any claim on either side.
- **Owner (2026-11-19):** "Decisions A–B on the claim universe (§11 #61) were taken after the extraction comparison had been seen, which broke the planned order (rubric questions resolved blind, then compare). Neither decision changed the classification of any claim on either side (`comparison_7a_decisions_AB.json`), so no reported figure depends on the sequencing. The lesson: parked rubric questions must be closed before the comparison is run, not alongside it."

### R48. A report opened with a blanket completion claim that its own body contradicted

- **What happened:** the seventh-session report opened "Everything is done and committed", and the same report then listed items that were not done (transcript capture in `copy_back`, the R2/R3/stress launch commands).
- **How it was caught:** by the owner, in the next prompt.
- **Fix:** reports now give the completion status item by item, with no blanket summary.
- **Implication:** a summary line is a claim too. It has to be true of every item, or be left out.

### R49. A claim's computed values were written into the session-log draft before being looked up

- **What happened:** the eighth-session draft described R1-D21-35 as "12 spare / 0 empty". The file gives 12 spare (strict) and **4** empty (rival).
- **How it was caught:** re-read before appending, under the verify-before-asserting rule (2026-11-18); corrected before the entry was written to `docs/SESSION_LOG.md`.
- **Fix:** the figure is now taken from `explanation_claims.json`.
- **Implication:** the fourth instance of the pattern (R43, R44, R46). Figures in prose need the same lookup as figures in code.

### R50. Owner-entered columns lived in files the converter regenerates

- **What happened:** `owner_claims.main` rewrites `non_mechanical_mappings.csv` and `adjudication_7a.csv` from scratch. Writing the owner's verdicts and causes directly into them would have been lost, silently, on the next converter run.
- **How it was caught:** while recording the owner's verdicts of 2026-11-19, before any rerun.
- **Fix:** the verdicts live in a committed input table (`owner_verdicts_nonmech.csv`); `owner_claims.main` re-applies it after regenerating (Log #106). A rerun was checked to leave the three files unchanged.
- **Implication:** still open for causes the owner types directly into `adjudication_7a.csv` (outside the table): a converter rerun would erase them. Parked (SESSION_LOG, 2026-11-19).
- **Closed (2026-11-19, §11 #62):** all owner judgements moved to input tables, with a rerun test (`tests/test_owner_inputs.py`).

### R51. A listing of a duplicate key was read as a duplicate rule

- **What happened:** the owner's instruction for r120–r123 said to "apply the duplicate rule you used for rows 54 and 57". No such rule was applied: the seventh-session comparison only listed rows 54 and 57 under `duplicate_keys_within_a_side`, and both are still counted (and matched) as separate claims. The session log line "Owner duplicate key: rows 54 and 57" said what was found, not what was done with it.
- **How it was caught:** checked `comparison_7a.json` and the converted claims before applying the instruction.
- **Fix:** the stated rule was applied to r120–r123 only (§11 #65); rows 54 and 57 are unchanged, and the figure with row 57 also collapsed is computed and labelled not applied (owner's derived 27/40 instead of 28/41).
- **Implication:** a report that lists a finding should say whether anything was done with it. The owner decides whether 54/57 get the same treatment.

### R52. The owner check of item 7 was proposed by an LLM advisor

- **Disclosure (owner, 2026-11-19).** Two sets of owner judgements were **proposed by an LLM advisor** (a separate Claude chat, **without repository access**, working from the tables the assistant generated) and were **reviewed and accepted by the owner**:
  1. the **43 adjudication causes** of item 7(a) (`owner_extraction/owner_adjudication_causes.csv`);
  2. **all 75 wrong-claim verdicts** of item 7(b) (`owner_review/owner_review_wrong.csv`): the 21 non-rubric-dependent (19 `confirmed_wrong`, 2 `extraction_error`) and the 54 rubric-dependent (`actually_correct`).
- **Consequence:** the owner check is **not independent of LLM judgement**. What stays independent is the owner's own extraction of days 3, 8 and 18 (`owner_claims_d03_d08_d18.csv`, frozen, SHA-256 `6c7af169…fd283c47`). Everything computed from the adjudication or the verdicts (the adjudicated recall, §11 #64–#67; the descriptive accuracy count, §11 #68) inherits this.
- **Implications (owner, 2026-11-19):** "The owner check therefore compares the assistant's extraction against a second LLM's reading plus my judgement. Errors that both LLMs share (for example the same misreading of a rubric term) would not be detected by it. The only fully independent evidence is my frozen extraction of days 3, 8 and 18, and on that sample all remaining discrepancies were on my side or in the rubric (0 assistant_miss, 0 assistant_encoding)."

### R53. A commit went through with two failing tests

- **What happened:** commit `009e156` was made by a command chain `uv run pytest -q | tail -1; git add -A && git commit …`. The suite reported "2 failed, 188 passed", but the exit status seen by the chain was `tail`'s (0), and the commit did not depend on the test result anyway. Both failures were in tests, not code: `test_owner_inputs` still asserted the review tables were empty (21 owner verdicts had just been entered), and the new `test_rubric_check_view` assumed a sentence split before a lowercase word that the splitter does not make.
- **How it was caught:** the assistant read the test summary line in the command output after the commit.
- **Fix:** both tests corrected; the fix was committed only after `uv run pytest -q` exited 0, checked on its own exit code.
- **Implication:** the "fast suite before each commit" rule (CLAUDE.md §9.4) was followed in form but not enforced. Gate the commit on pytest's exit status, never on a pipeline that ends in `tail`.

### R54. A display file labelled cardiology and internal medicine the wrong way round

- **What happened:** `unverifiable_view.py` built its department labels as `zip(DEPARTMENTS, ("CA", "IM", "NE", "OR"))`, but `DEPARTMENTS` starts with internal medicine. Every per-department value in the first generated `unverifiable_26_check.csv` had its CA and IM labels swapped (for example R1-D30-47/48 showed 28/29 instead of the ALLOCATOR's 29/28).
- **How it was caught:** the generated values were compared with the same quantities computed beforehand in a scratch run that named the departments explicitly; the two disagreed on CA and IM.
- **Fix:** labels keyed by department name, with an assertion that they cover `DEPARTMENTS`; a test pins CA/IM and the day-30 values. No other module zips `DEPARTMENTS` with abbreviations (checked). The faulty file was never committed.
- **Implication:** never rely on the order of a shared constant for labels; cross-check a new generator against an independent computation before reporting from it.


### R55. A pre-flight comparison passed vacuously on wrong field names

- **What happened:** to compare the new run-settings probe with the committed pre-R1 baseline, the first script read the fields `outcome` / `status` / `result` and `leaks`, which do not exist in `run_settings_verification.json` (the fields are `denied` and `leak_markers`). Every call was classified `(None, False)` on both sides, so the comparison reported "same classification: True" without comparing anything.
- **How it was caught:** the script also printed the record's keys; they did not match the fields used, so the result was discarded before being reported.
- **Fix:** redone on `denied` and `leak_markers`: 30/30 calls classified identically to the baseline, 21 denied, 0 leak markers.
- **Implication:** an equality check between two records is evidence only if the compared fields exist; read the schema first, or fail on missing keys (`c["denied"]`, not `c.get(...)`).

### R56. Copy-back's tool-results branch was never tested at the path lengths of a real run

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** R2's copy-back (2026-11-22) stopped inside `allocator_digest.preserve` with `FileNotFoundError: [WinError 3]` on the first spilled tool result. The destination `results/allocations/R2/transcripts/subagents/allocator/tool-results/mcp-allocator-get_decision_history-1795337149486-we0rir.txt` is 260 characters under the OneDrive repository root (132). `LongPathsEnabled` is 0, and MAX_PATH (260) includes the terminating NUL, so 259 is the longest usable path. The parent folder had been created (`put` already did `mkdir(parents=True)`), so a missing directory was not the cause.
- **Why it slipped through:** the branch was covered by tests (`test_allocator_digest`, `test_copy_back`), but only under short `tmp_path` folders with short names, so the tests never reached the length a real run reaches. DRY3 had no tool results. R1's were captured earlier, and its names had no random suffix (253 characters). R2's Claude Code names add 7 characters (`-we0rir`), which pushed the path over the limit. The failure surfaced only at the first real run that needed the branch. Git had the same limit: `git add` refused the files ("Filename too long") until `core.longpaths` was set.
- **Consequence:** none on the data. The attempt left both run folders complete and hash-identical to the clone, and 72 of 85 capture files (all transcripts and metadata) hash-identical to the session folder. The 13 tool results, `SHA256SUMS.json`, the run report and `copy_back.json` were missing. Nothing was overwritten, and the clone and the session folder were not touched.
- **Fix:** long-path-safe copy and hashing (Log #116), and a hash-verified `--resume`. The new tests place the files over 260 characters with R2's exact name shape; with `long_path` disabled, the test reproduces the R2 error. R2 was completed with `--resume`: 85/85 files and 9 + 3 run-folder files hash-identical, 0 mismatches.
- **Implication:** a test of a file-system branch must use the real path lengths and name shapes, not only the real logic. Any capture step whose inputs are named by an external tool (here Claude Code) must expect those names to change between versions.

### R57. A file count in the R2 copy-back report was given the wrong label

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** the report on fc5a944 said the failed attempt wrote "both run folders in full (84 files)" and, a few lines later, "run folders: hash-identical to the clone (9 + 3 files)". The 84 was every R2 file in the repository after the failed attempt: 12 run-folder files plus 72 capture files. Both numbers were right, but the first was attached to the wrong noun, so the report contradicted itself.
- **How it was caught:** the owner's review.
- **Fix:** re-hashed and reported separately. Allocations: 9/9 clone files matched; 95 in the repository = 9 + 86 capture (85 files plus `SHA256SUMS.json`). Evaluations: 3/3 matched; 5 = 3 + `copy_back.json` + `run_report.json`.
- **Implication:** every count in a report needs the set it counts named, and two counts of overlapping sets need their relation stated (84 = 12 + 72).

### R58. Two flaws in the first long-path fix, found while extending it to readers

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** (i) `long_path` built the extended form from `Path.absolute()`, which does not collapse `..`, and the extended form disables Windows' own normalisation. A path containing `..` would have pointed to a file that does not exist. No caller passed one, so there was no consequence. (ii) The first routing of `Store` wrapped its `alloc_dir`/`eval_dir` attributes, which changed values that callers compare.
- **How it was caught:** (i) on re-reading `paths.py` while routing the readers; (ii) by `test_store_paths_resolve_relative_to_the_run_folder` in the fast suite.
- **Fix:** `os.path.abspath`, plus a test with `..` and a test that applying the function twice gives the same result. `Store` routes only its read calls.
- **Implication:** a path helper that bypasses the OS's normalisation must do that normalisation itself. A wrapper belongs at the I/O call, not on public attributes.


### R59. Default output paths of the evaluation entry points point into the frozen run folders

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** the clean-up inventory (2026-11-23) found that `metrics.evaluate_run` defaults to `results/evaluations/<run>/` and writes `deterministic_audit.jsonl` and `metrics.json` there. `run_report` and the `claim_check` CLI also write inside the run folder, and `python -m src.evaluation` rewrites the baseline records with a new `created_at`. For R1–R3 and STRESS1, `deterministic_audit.jsonl` is a copy-back file whose hash is recorded in `copy_back.json`. A recomputation with the defaults, for example a "headline number recomputed without the agent", would have overwritten frozen evidence with a file that differs at least in `created_at`.
- **How it was caught:** by reading the writers while auditing path dependencies for the clean-up plan. Nothing was run with the defaults, and nothing was overwritten. The Phase 0 independent check passed on all four runs the same day.
- **Fix (planned, Phase 1b):** output-root options on these entry points, numbered scripts that always write under `results/analysis/recomputed/`, and tests that the committed files are untouched (`docs/CLEANUP_PLAN.md` §3.3, §9 step 5).
- **Implication:** a default output path that suits the first run turns into a hazard once that output is frozen. Recomputation for verification must write somewhere new and then compare.

### R60. The clean-up plan's list of writers into run folders was incomplete

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** `docs/CLEANUP_PLAN.md` §3.3 (R59) named `metrics.evaluate_run`, `run_report`, `claim_check` and `python -m src.evaluation` as the entry points that write into run folders. A full scan of the writers at the start of Phase 1b found more: `allocator_digest.digest` (writes `results/evaluations/<run>/allocator_digest/`) and the R1 owner-review modules (`owner_claims`, `owner_verdicts`, `owner_inputs`, `owner_review_counts`, `claim_review`, `decisions_ab`, `adjudication_view`, `adjudication_recall`, `rubric_check_view`, `unverifiable_view`), which write into `results/evaluations/R1/`. The MCP server's `Store` and `launch` also write into run folders.
- **How it was caught:** while implementing the owner's guard, by grepping every `write_text`, `open(..., "w"/"a")`, `mkdir`, copy and replace call in `src/` instead of relying on the plan's list.
- **Fix:** the guard sits in one helper that every writer calls, so coverage does not depend on a hand-made list. A test greps `src/` for write calls in modules that do not call the guard.
- **Implication:** an inventory of "who writes where" has to come from a search of the code, not from memory of the modules recently worked on. This is the same lesson as R56, from the other side.

### R61. A fast-suite test rewrote a file inside the frozen R1 folder on every run

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** `tests/test_long_paths.py::test_owner_review_entry_points_at_long_paths` called `owner_review_counts.main("R1", <repo>/results/evaluations/R1)` to compare counts. That call rewrites `results/evaluations/R1/owner_review/claim_accuracy_after_owner_review.json` in the repository. The bytes were identical each time (so `git status` stayed clean and nothing showed), but every run of the fast suite since Log #117 wrote into a frozen run folder.
- **How it was caught:** during Phase 1b, by reading the tests that call writers on committed run folders while adding the frozen-run guard. The guard now raises on that call.
- **Fix:** the test runs the module only on its deep temporary copy (whose outputs are already compared byte for byte with the committed ones) and asserts that the call on the committed folder raises `FrozenRunError`.
- **Implication:** "byte-identical rewrite" leaves no trace in `git status`, so it is invisible. A test that only reads frozen evidence must not call a function that writes.

### R62. Uncommitted, unlogged work on `cleanup` after a "clean `git status`" hand-off

- **Type:** development/process (not a finding about agent reliability).
- **What happened:** the hand-off for the 2026-11-24 session reported a clean `git status` at the end of Phase 1b. At session start, 12 tracked files under `src/` were modified (`src/08_claim_verification.py`, the nine owner-review modules, `src/utils/compare.py`, `src/utils/paths.py`): an unfinished version of the owner-review `--out` redirect, citing a Decisions Log #125 that did not exist. Merging with it would either have failed or carried untested, unlogged code into `main`.
- **How it was caught:** `git status` at session start, before any edit.
- **Fix:** the work was stashed (`stash@{0}`), the plan.md wording was committed and merged without it, and the stash was then reviewed, finished, logged (renumbered to #127) and tested as the follow-up of item 2.
- **Implication:** a hand-off's "clean `git status`" is a claim to be checked at the next session start, like any other.
