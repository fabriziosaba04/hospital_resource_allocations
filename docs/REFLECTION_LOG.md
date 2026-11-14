# Reflection Log

A running record of things that went wrong, or nearly went wrong, during the project. It is source material for the final Reflection (`LIMITATIONS_AND_REFLECTION.md`) and for the Verification section of the report.

**Rule (owner, 2026-11-11):** add an entry **at the moment** something like this happens, not at the end of a session, and mention new entries in the session report. Errors by the AI assistant count as much as errors in the code or the design.

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
