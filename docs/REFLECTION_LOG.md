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

- **What happened:** the smoke-test design assumed the dispatcher would follow a one-off user prompt replacing its loop with mechanical steps: subagents calling their own tools without judgement, trying foreign tools, and a test spawn of an `Explore` subagent. The dispatcher refused. It answered that its protocol allows only the fixed workflow steps and the two fixed prompts, and ran its **normal loop**. The ALLOCATOR and CHECKER, with the **draft prompts the owner has not yet reviewed**, therefore made real decisions for 5 days and wrote a validation report. This happened on the synthetic SMOKE5 fixture with haiku; no frozen dataset was touched. But it is not what the owner asked for ("draft the prompts for my review; don't run any agent session"). A first attempt had stopped after one call, for the same reason.
- **How it was caught:** the smoke script classifies the transcript and keeps the dispatcher's final text, which states the refusal. Every call the dispatcher made was a workflow tool or one of the two fixed templates, word for word.
- **Implication:** the refusal is itself good evidence for dispatcher neutrality: a system prompt that forbids improvising held against a direct user instruction. But a test that needs an agent to step outside its role cannot be run through that agent. The assistant should have predicted this from the dispatcher prompt it had just written. Check 5c (the dispatcher cannot spawn other subagents) could not be shown live, because the dispatcher never tried.
- **Decisions Log:** #69, #70.

