# Session Log

One entry per working session, newest last. Each entry records what was achieved, the state of the repository, the ordered next steps and the questions waiting for the owner. `PROJECT_SPEC.md` §0 points to the latest entry. Decisions themselves live in `PROJECT_SPEC.md` §9 (Implementation Decisions Log) and §11 (owner decisions); errors and near misses in `REFLECTION_LOG.md`.

---

## 2026-11-12

Commits of the day: `4b54ad7` … the session-close commit (see `git log`). Tag `data-v1.0` unchanged.

### Achieved

**Milestones**

1. **Metric formulas and CHECKER severity scale fixed before any agent output** (§11 #16–#23; `EVALUATION_PLAN.md` §3–§4).
2. **Environment complete; audit, metrics and baselines complete** (Log #53–#58). B0–B2 run on all four datasets; every run passes the gate.
3. **Headline set confirmed after the headroom review** (§11 #24–#28).
4. **Milestone 2: MCP server, agent files, smoke test 22/22** (Log #61–#76), with check 5c shown live through a versioned probe agent.
5. **Pre-R1 robustness** (§11 #33; Log #79–#81): HALTED with a recorded reason, stale-lock handling, resumable idempotent writes. Tested by killing a run at 12 points and resuming; the records equal an uninterrupted run's.
6. **Dry run DRY1-SMOKE5** on the synthetic fixture with `claude-sonnet-5-5` and the R1 launch command (results below).

**Key decisions**

- Internal deadline 30 November (Log #45).
- Testing and documentation policy (`CLAUDE.md` §9.4, Log #58).
- **Framing** (§11 #24): B1, a greedy rule, is at or near the floor on A1–A3. The question is whether the LLM system reliably reproduces a near-optimal myopic policy, where it deviates, and whether the CHECKER catches the deviations. The agent is not expected to beat B1 on clinical metrics, and the data stay frozen.
- **Headline:** A1, A2 per tier, A3 tiers 3 and 2, each read as the gap to B1 and to the floor; gate D. Fairness dispersion is not promoted (§11 #25).
- **Stability secondary:** all reversals only, with the statement that reversals have no cost in the model; the occupied-reversal count was dropped (§11 #26, #32).
- **Agent visibility redesign** (§11 #29, superseding Log #6): the CHECKER is blind to the deterministic audit and gets read-only record tools plus a past-day what-if. Both what-ifs return outcomes only. The labels sit behind an off-by-default "assisted" flag.
- **Model:** `claude-sonnet-5-5` for all roles, in the run settings (§11 #31).
- **Prompt development** only on the synthetic fixture; freeze at `prompts-v1.0` before R1 (§11 #34).
- **The CHECKER's deterministic definitions match the audit's** (§11 #35, Log #84).

**Main findings**

- **Headroom** (`EVALUATION_PLAN.md` §8): SV_B is 257–280 for B0 and 0 for B1. B1's headroom above the floor is at most 2.3 nurse-days (A2) and 4 patient-days (A3 path). Bed reversals are mostly empty-bed churn (R19). Seed 09 cannot discriminate B1 from B2 on bed metrics.
- **Design error caught at prompt review** (R25): the design approved on 2026-11-07 gave both agents the evaluation's answers. The CHECKER could read the audit, and the what-if labelled violations (and showed the A2 tier gaps).
- **Dry run** (below): the plumbing, the dispatcher, the ALLOCATOR's process and the resume-safe records work. The CHECKER's matching against the audit shows recall 0.43, all of it a reversal counting and reference issue (R28). The fixture contained no clinical-priority case to detect (R29).

### Dry run DRY1-SMOKE5: results for the owner's review

Setup: synthetic SMOKE5 fixture (5 days, 4 departments, pool 14 beds, 12 on day 3; 5 nurses; mean census 20.6). Labels flag off. Launched with `python -m src.mcp_server.launch`, one launch, no interruption. The models observed in the transcript equal the configured ones (`claude-sonnet-5-5`, main session and subagents). Final state FINISHED; consistency check clean. Records: `results/allocations/DRY1-SMOKE5/`; report: `results/evaluations/DRY1-SMOKE5/run_report.json`.

| Day | Accepted on attempt | What-if calls (validate) | Beds IM / CA / NE / OR | Nurses IM / CA / NE / OR | Audit issues | Wall clock | ALLOCATOR tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 3 (0) | 4 / 5 / 2 / 3 | 1 / 3 / 0 / 1 | none | 37 s | 16,316 |
| 2 | 1 | 3 (0) | 4 / 5 / 3 / 2 | 1 / 2 / 1 / 1 | 2 × nurses_reversal (Minor) | 36 s | 17,873 |
| 3 | 1 | 3 (0) | 2 / 5 / 3 / 2 | 1 / 2 / 1 / 1 | none | 34 s | 19,399 |
| 4 | 1 | 2 (0) | 5 / 2 / 3 / 4 | 2 / 1 / 0 / 2 | 2 × beds_reversal (Minor) | 34 s | 19,525 |
| 5 | 1 | 3 (1) | 5 / 1 / 5 / 3 | 2 / 0 / 2 / 1 | 1 × beds_reversal, 2 × nurses_reversal (Minor) | 134 s (with CHECKER) | 22,098 |

- **Hard constraints:** no rejected submission, no repair day, no hard-constraint error.
- **Clinical:** no bed pair, no nurse gap and no F1 inversion on any day. The fixture never created one (R29).
- **CHECKER report** (day 5, 4 issues, CHECKER 44,195 tokens, 99 s):
  - nurses_reversal on days 2 and 5, and beds_reversal on day 4, each reported **once for both departments** of a round trip;
  - one explanation_inaccuracy (Moderate): day-1 alternative C lists L3 shortages 0.6 + 0.6 + 0.6 but states the total as 1.2. **Verified in the decision record.** It did not affect the choice: corrected, C totals 1.8, worse than the chosen B at 1.4.

  The CHECKER also wrote that it could not compute the reference allocation for the day-4 reversal exactly.
- **CHECKER versus audit** (deterministic, `checker_matching.py`): 7 audit issues, 3 CHECKER issues of matchable types, 3 matched.
  - **recall 0.43, precision 1.0, level agreement 1.0**;
  - per type: nurses_reversal 2 of 4, beds_reversal 1 of 3;
  - every miss is the second department of a round trip, or the day-5 bed reversal that depends on the reference allocation (R28).
- **Cost and time:** $0.78 (list price, `costBasis: list`), 295 s in total. ALLOCATOR about 30 s and 16–22k tokens per day, rising by about 1.4k tokens a day as the decision history grows. CHECKER 99 s and 44k tokens.
- **Extrapolation to 30 days (rough):**
  - At fixture scale, ALLOCATOR tokens grow to about 57k on day 30, about 1.1M in total, plus about 6 × 45–60k for the CHECKER. That is about 10 times the dry run: about $8 and 30–40 min.
  - The primary dataset has about 4.3 times the census (87.8 against 20.6), and the overflow queue and what-if outputs grow with it, so expect roughly 2–3 times that: **about $15–25 at list price and 45–90 min**.
  - On a subscription this is usage-limit consumption, not dollars. A 30-day run may well be interrupted, which is why the resume path was built and tested.
- **Unexpected in the transcripts:**
  1. The dispatcher launches subagents in the background and waits for their completion notices; it worked every time.
  2. The ALLOCATOR called `validate_allocation` only once in 5 days. It relied on the what-if's hard-constraint result, which is the same validator.
  3. The CHECKER merged the two departments of each reversal into one issue, against the stated counting unit.
  4. No tool errors, no rejected submissions, no off-protocol dispatcher action.

### State

- **Built:** data generation and validation; environment; deterministic audit, metrics, baselines and headroom; MCP server (state machine, record store, ANALYZER, three role servers), agent files, launcher, consistency check, run report, CHECKER matching; smoke test and run-settings verification scripts.
- **Frozen or tagged:** data at `data-v1.0` (manifest OK). Metric formulas, severity scale and headline set fixed (§11 #16–#28). **Prompts not frozen; no `prompts-v1.0` tag yet.**
- **Tests:** fast suite and full suite pass at the session-close commit (see the commit message). Manual: smoke test 22/22; run-settings verification passed (19 protected reads denied).
- **No run on frozen data.** No ACTIVE_RUN pointer is set (the dry run's pointer was removed at session close).
- **Still open:** the owner's dry-run review and the questions below; visualization (deferred).

### Next session

1. **Owner reviews this dry run** and answers the open questions below.
2. Apply the decisions, on the synthetic fixture only (§11 #34). If prompts or definitions change, run another dry run (with the harder fixture, if approved) and review it.
3. **Tag `prompts-v1.0`** (prompts and run settings frozen).
4. Pre-R1 checks: `verify_run_settings.py`, the smoke test, the full suite, the manifest check.
5. **R1** on `seed20261107` (`init_run --dataset seed20261107 --run-id R1`, then `launch`; resume with the same command if interrupted), then the run report and the metrics.
6. R2, R3, the stress run (reported separately), the robustness appendix, visualizations and the report, by 30 November.

### Open questions for the owner

1. **Reversal matching (R28).** The CHECKER cannot compute the reference allocation, and it merged round-trip departments. Options:
   - (a) expose the reference allocation (and τ) in the CHECKER's `get_allocation_state`. It is derived from the records, but it is an audit intermediate;
   - (b) define reversals for both the audit and the CHECKER on the plain day-to-day change, excluding pool-change days. That changes an approved metric;
   - (c) leave it, and report reversal matching separately as a known definitional limit.

   *Recommendation: (a), with the counting unit restated in the prompt as "two issues for a round trip between two departments".*
2. **Harder synthetic fixture (R29)** for the next dry run: more patients and pressure, a pool cut that forces a shock cut, and nurse rationing, so that the CHECKER faces clinical-priority cases. *Recommendation: yes.* It is synthetic, so it stays within §11 #34.
3. **Severity-scale wording vs. the audit.** The approved scale says "a rejected submission later corrected the same day" is Moderate; the audit (and now the prompt) counts **every** rejected submission as Moderate, and a failure day additionally as Major. *Recommendation: align `EVALUATION_PLAN.md` §4 to the audit.*
4. **Unobservable Minor item.** "A modification submitted without a `simulate_allocation` call" cannot be detected by the audit or the CHECKER, because what-if calls are not recorded. *Recommendation: drop it from the scale, or record what-if calls in the workflow log (visible to the CHECKER through its tools) if the owner wants it measured.*
5. **Cost.** At the extrapolated $15–25 (list) and 45–90 min per 30-day run, are R1–R3 plus the stress run (four runs) acceptable, or should R2/R3 be conditional on R1?

---

## 2026-11-14

Time-boxed session (90 min; started 16:27). Commits: `6bacee7` (DRY1 review), `c2db023` (hard fixture), `81c2cf4` (run-settings re-verification), and the session-close commit. Tag `data-v1.0` unchanged; **no `prompts-v1.0` tag**. **No run on frozen data.**

### Achieved

1. **DRY1 review applied** (owner decisions §11 #36–#41; Log #85–#87):
   - the CHECKER's `get_allocation_state` returns the reference allocation and τ per day, which a test shows equal the audit's;
   - `checker.md` counts a round trip as one issue per department;
   - CHECKER matching is stratified by type, level and group (headline, secondary, other);
   - the severity wording is aligned to the audit (every rejected submission is Moderate, a failure day is Major);
   - "change submitted without simulating it" is dropped;
   - what-if and validate calls are logged to `process_calls.jsonl`, read by no tool;
   - the R1–R3 pre-commitment is in `EVALUATION_PLAN.md` §6.
2. **Hard synthetic fixture HARD10** (`src/mcp_server/fixture_hard.py`, Log #88): seed 20261114, 10 days, 103 patients. `tests/test_fixture_hard.py` (7 tests) asserts every guaranteed condition. The forced cut is guaranteed only for allocations that fill every bed on day 7 (R31).
3. **DRY2-HARD10** run with the R1 launcher, settings and model, after the run-settings verification (19 protected reads denied, no leaks), the full suite (150 passed) and the manifest check (OK).

### DRY2-HARD10: results for the owner's review

One launch, exit 0, FINISHED, consistency check clean, models as configured (`claude-sonnet-5-5` everywhere). **Every decision was accepted on the first attempt**; no repair, no hard-constraint error.

| Day | Pools (beds/nurses) | Beds CA/IM/NE/OR | Nurses CA/IM/NE/OR | Audit issues | ALLOCATOR calls (sim/val) | ALLOCATOR tokens | Wall (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 20/6 | 4/10/1/5 | 2/2/1/1 | – | 2/0 | 11.8k | 31 |
| 2 | 20/6 | 9/6/2/3 | 3/1/1/1 | nurse_gap (Moderate) | 2/1 | 15.9k | 42 |
| 3 | 20/6 | 9/6/2/3 | 4/1/1/0 | – | 2/0 | 15.7k | 34 |
| 4 | 23/8 | 10/4/1/8 | 5/1/1/1 | 2 beds_rev, 1 nurses_rev | 2/0 | 17.7k | 31 |
| 5 | 23/8 | 10/5/2/6 | 6/1/1/0 | 2 beds_rev | 2/0 | 19.1k | 141 (with CHECKER) |
| 6 | 20/6 | 10/6/1/3 | 5/0/1/0 | 2 beds_rev | 3/1 | 23.6k | 40 |
| 7 | 20/6 | 10/6/2/2 | 5/0/1/0 | nurse_gap (Moderate) | 3/1 | 26.2k | 44 |
| 8 (shock) | 11/5 | 7/2/2/0 | 4/0/1/0 | nurse_gap (Moderate) | 2/1 | 28.2k | 48 |
| 9 | 11/5 | 7/2/2/0 | 3/1/1/0 | nurse_gap (Moderate), 2 nurses_rev | 2/0 | 29.0k | 35 |
| 10 | 20/6 | 8/4/4/4 | 3/2/1/0 | 2 beds_rev | 2/0 | 28.7k | 157 (with CHECKER) |

- **Beds: no bed pair, no F1 inversion and no shock-cut issue on any day.** Under B0 and B2 the same fixture gives (3,1) and (2,1) displaced pairs and F1 inversions. The ALLOCATOR avoided all of them, as B1 does.
- **Day 8 was a real forced cut:** 20 beds were filled on day 7, 14 holders faced 11 beds, and exactly 3 beds were cut with no avoidable pair.
- **Nurses:** a Moderate nurse gap (tier 2 only) on days 2, 7, 8 and 9; no tier-3 gap.
- **CHECKER reports:** day 5, 8 issues, 41.6k tokens; day 10, 9 issues, 48.9k tokens; 5 past-day what-ifs in total.
- **CHECKER versus audit, stratified** (all reports pooled, `checker_overall` in the run report):

  | Stratum | Audit | CHECKER | Matched | Recall | Precision | Level agr. |
  | --- | --- | --- | --- | --- | --- | --- |
  | **Headline group** | 4 | 4 | 4 | **1.0** | **1.0** | 1.0 |
  | – of which `nurse_gap` | 4 | 4 | 4 | 1.0 | 1.0 | 1.0 |
  | Secondary group | 11 | 11 | 9 | 0.82 | 0.82 | 1.0 |
  | – `beds_reversal` | 8 | 8 | 6 | 0.75 | 0.75 | 1.0 |
  | – `nurses_reversal` | 3 | 3 | 3 | 1.0 | 1.0 | 1.0 |
  | Other group | 0 | 0 | – | – | – | – |
  | By level: Moderate / Minor | 4 / 11 | 4 / 11 | 4 / 9 | 1.0 / 0.82 | 1.0 / 0.82 | 1.0 / 1.0 |
  | Pooled (reference only) | 15 | 15 | 13 | 0.87 | 0.87 | 1.0 |

  - The two bed-reversal misses are day placement: the audit has 2 on day 6, the CHECKER put them on days 7 and 8.
  - With the reference allocation exposed, round trips are now counted per department, as defined (R28).
  - **The headline group is all `nurse_gap`.** The CHECKER's detection of bed-type violations is still untested on positives, because the ALLOCATOR made none. It reported no false bed issues (true negatives only).
- **LLM-only issues, checked by hand against the records:**
  - (1) day 2, "moving orthopedics' only nurse would be no better". **Correct:** the audit's day-2 nurse gap confirms that a split with equal level-3 and +0.40 level-2 coverage existed.
  - (2) day 2, "keeping the allocation would leave 4 beds empty in IM and orthopedics and overflow 5 level-3 patients". **Partly correct:** keeping the allocation would leave **5** beds empty (IM 3, OR 2), so "4" is wrong. The 5 level-3 overflow figure is right, although the CHECKER called both figures wrong.
- **Cost and time:** $1.64 (list price), 628 s, 44 dispatcher turns. ALLOCATOR 11.8k → 28.7k tokens per day (about +1.9k a day, from the growing decision history); CHECKER 42–49k per audit.

### Point 7a: dispatcher context growth (analysis only)

| | Base (day 0) | Per normal day | Per audit day | Day 5 | Day 10 |
| --- | --- | --- | --- | --- | --- |
| DRY1-SMOKE5 | 17.8k | +1.1–1.5k | +2.2k | 25.4k | – |
| DRY2-HARD10 | 18.1k | +1.2–1.5k | +2.2–2.3k | 25.6k | 33.4k |

(The context of each dispatcher turn = input + cache-read + cache-creation tokens, from the stream-json transcript.)

- The increments are almost identical on two fixtures of different size and difficulty. The dispatcher sees only workflow-status JSON and the subagents' short final texts, never hospital data, so its growth **does not scale with the dataset**.
- **Extrapolation to 30 days on the primary dataset:** 18k + 24 × 1.4k + 6 × 2.3k ≈ **66k tokens**; allow up to about 80k for longer subagent summaries.
- The transcript reports a 1,000,000-token context window for `claude-sonnet-5-5`, so that is under 10%. **A mid-run compaction is very unlikely.** No compaction event occurred in either dry run.
- **Recommendation: no change.** If the owner wants a guard anyway, the cheapest is a launcher option that ends the session after N days (for example 10) and relaunches, relying on the tested resume. I do not recommend it: it adds launches without a measured need.
- The ALLOCATOR (a fresh subagent each day, about +1.9k tokens a day from the decision history) grows faster. It reaches an estimated 70–120k tokens by day 30 at primary scale, still far below the window.

### Point 7b: OneDrive (analysis only)

- **Risk:** during a run the server replaces `state.json` atomically, creates a lock file with `O_EXCL`, and appends to JSONL records many times a minute. OneDrive can briefly hold or rewrite these files, or create conflict copies. Files On-Demand can also turn data files into placeholders. Today's mitigation is only the 2-second retry on `os.replace` (Log #79).
- **Recommendation: run R1–R3 and the stress run from a clone outside OneDrive** (for example `C:\hra-runs\hospital_resource_allocations`):
  1. `git clone` the repository there, then `git checkout prompts-v1.0` (exact frozen code, prompts and data, clean tree), then `uv sync`.
  2. In the clone: manifest check, `verify_run_settings.py`, `init_run`, `launch`. Resume with the same command.
  3. **Getting results back:** copy `results/allocations/<R>` and `results/evaluations/<R>` into the OneDrive repository. Verify that the SHA-256 of every copied file matches the clone, re-run the consistency check, build the run report in the repository, and commit.
     - `run_manifest.json` keeps the clone's absolute `data_root` and `eval_dir`, which is correct as provenance.
     - `run_report` and the consistency check read paths from the manifest, so an `--eval-dir` override (or reading relative to the run directory) is needed to rebuild reports in the repository. That is a small code change to make **before** the tag.
- **Fallback:** pause OneDrive sync for the run. OneDrive offers 2, 8 or 24 hours. It needs no code, but it is manual and easy to forget, and it resumes on its own.

### State

- **Built:** everything listed on 2026-11-12, plus the reference-allocation tool output, stratified matching, the process-call log, the HARD10 fixture and its tests, and the DRY2 records and report (`results/allocations/DRY2-HARD10`, `results/evaluations/DRY2-HARD10/run_report.json`).
- **Tests:**
  - fast suite passed at each commit;
  - full suite 150 passed;
  - manifest OK;
  - run-settings verification passed (19 denied, no leaks).
- No ACTIVE_RUN pointer is set (removed at session close; DRY2 is finished).

### Where the session stopped

After step 4 (DRY2 and its report), inside the time box. Nothing is half-applied.

### Next session

1. **Owner reviews DRY2** and answers the questions below. No `prompts-v1.0` tag and no run on frozen data before that.
2. Apply the decisions. If prompts change, re-run a dry run on HARD10.
3. If the clone procedure is approved: add the eval-dir override, then tag `prompts-v1.0`.
4. Pre-R1 checks in the run location (verification, smoke test, full suite, manifest), then R1 under the pre-commitment (§11 #40).

### Open questions for the owner

1. **Bed-violation detection by the CHECKER is still untested on positives**, because the ALLOCATOR made no bed errors on HARD10. Options:
   - (a) accept it, and report the true negatives;
   - (b) run the LLM CHECKER alone on the **B2 run of HARD10**, which has (3,1), (3,2) and (2,1) displaced pairs and F1 inversions. That measures bed detection independently of the ALLOCATOR. Baseline records have no explanations, so the CHECKER would audit allocations only. It needs a small run-init path that loads baseline records into a run directory.

   *Recommendation: (b)*, on the synthetic fixture only, before the tag.
2. **Group for `rejected_submission` and `f1_inversion`** in the stratified matching: they are in neither the headline nor the secondary list. *Recommendation:* `rejected_submission` in the headline group (a hard-constraint breach caught by the validator); `f1_inversion` in secondary (a fairness concern). Currently they are reported as "other".
3. **OneDrive:** approve the run-from-a-clone procedure (7b), including the small eval-dir override before the tag, or choose pausing sync.
4. **Reversal day placement:** the CHECKER placed 2 of 8 bed reversals one or two days late, even with τ exposed. Accept this as a CHECKER error, which is what the matching should measure, or clarify the dating in `checker.md`? *Recommendation: accept.* The prompt already defines it, and changing it after seeing the result would tune the prompt to the matching.
