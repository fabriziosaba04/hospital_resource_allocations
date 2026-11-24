# Hospital Resource Allocation Agent

A decision-support agent that reallocates **beds and nurses** across four departments (Internal Medicine, Cardiology, Neurology, Orthopedics) of a **simulated** hospital, one day at a time, putting clinical priority first, then fairness, then efficiency.

- An LLM **ALLOCATOR** decides through the tools of a local MCP server.
- Deterministic components analyse the hospital, enforce the workflow and audit every decision.
- An LLM **CHECKER** reviews the decisions every five days.

The agent is compared with three deterministic baselines on synthetic data. It is a course prototype (Business Analytics), not a system for running a real hospital or replacing human decisions.

## Five-minute path

1. **What it is.** An LLM agent system (ALLOCATOR and CHECKER, run as Claude Code subagents against a local MCP server) that reallocates beds and nurses daily in a simulated four-department hospital. It is compared with three deterministic baselines (B0 no reallocation, B1 clinical-priority-first, B2 proportional) on frozen synthetic data, and every decision is audited by deterministic code.
2. **The headline result:** [`ANALYSIS.md`, Key results](ANALYSIS.md#key-results), with the reach of the results in [§5 Limitations](ANALYSIS.md#5-limitations). Every number there is listed with its source file in [`results/analysis/HEADLINE_NUMBERS.csv`](results/analysis/HEADLINE_NUMBERS.csv).
3. **The brief's deliverables:** code ([`src/`](src/), [`.claude/agents/`](.claude/agents/)), this README, [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md), [`REFLECTION.md`](REFLECTION.md); the full map is in §1.
4. **Verify in a few commands** (from a clone or the zip; see §5 for setup):

   ```bash
   uv sync
   uv run pytest -q                                # fast test suite
   uv run python src/01_verify_data.py             # frozen data against data/MANIFEST.json
   uv run python src/05_verify_copy_back.py        # re-hash all four agent runs (--sums-only mode)
   uv run python src/14_write_analysis.py --check  # ANALYSIS.md matches the committed tables
   uv run python src/16_error_analysis.py --check  # ERROR_ANALYSIS.md matches its tables and register
   ```

   Each prints OK / EQUAL / "up to date" or exits non-zero.

**Overview.** A fixed split of beds and nurses soon becomes unbalanced: one department overflows while another has idle beds, and nurse shortages fall unevenly on patients. Each simulated day, the ALLOCATOR reassesses the split under hard rules:

- resources are never created;
- occupied beds are never taken away, except when an external shock cuts the bed pool;
- each department has the same bed cap;
- every decision is explained and recorded.

Patients have one of three complexity levels (Level 3 is the highest priority). Agents never see future data or the parameters that generated the data. The full statement of principles and constraints is in [`CLAUDE.md`](CLAUDE.md).

## 1. The deliverables

| Brief | Where |
| --- | --- |
| Code for the agents | Agent definitions (dispatcher, ALLOCATOR, CHECKER): [`.claude/agents/`](.claude/agents/). Run restrictions: [`.claude/run-settings.json`](.claude/run-settings.json). MCP server (ANALYZER, ORCHESTRATOR state machine, tools): [`src/mcp_server/`](src/mcp_server/). Deterministic environment rules: [`src/environment/`](src/environment/). Audit, metrics and baselines: [`src/evaluation/`](src/evaluation/). The pipeline in run order: [`src/01_verify_data.py`](src/01_verify_data.py) … [`src/16_error_analysis.py`](src/16_error_analysis.py) (§5) |
| README | this file |
| Error analysis | [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md): the agents' errors in the runs (A), the coding agent's errors during development (B), errors in the verification itself (C), and how each was found (D); every number listed in [`results/analysis/ERROR_NUMBERS.csv`](results/analysis/ERROR_NUMBERS.csv). [`mistakes.md`](mistakes.md) points to it |
| Reflection (one page) | [`REFLECTION.md`](REFLECTION.md) (long version [`docs/LIMITATIONS_AND_REFLECTION.md`](docs/LIMITATIONS_AND_REFLECTION.md)) |
| Analysis (results) | [`ANALYSIS.md`](ANALYSIS.md): R1–R3 against the baselines, run by run; the CHECKER against the audit; the CHECKER on R1's wrong claims; the STRESS1 probe; the limitations (§5). Every number is listed with its source file and script in [`results/analysis/HEADLINE_NUMBERS.csv`](results/analysis/HEADLINE_NUMBERS.csv) |
| Plan (question, theory, test) | [`plan.md`](plan.md), which summarises [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md). No numerical falsification threshold was pre-registered: a run failing gate D counts against the hypothesis, and gaps to B1 are reported run by run (a declared limitation) |

**Two files about "agents".** [`CLAUDE.md`](CLAUDE.md) holds the standing instructions for the coding agent (what the brief calls `AGENTS.md`). [`docs/AGENTS.md`](docs/AGENTS.md) specifies the system's own four agents: ANALYZER, ALLOCATOR, CHECKER and ORCHESTRATOR.

## 2. Where the evidence is

| Grading axis | Evidence |
| --- | --- |
| **Analysis (50%)** | Results: [`ANALYSIS.md`](ANALYSIS.md), from the tables in [`results/analysis/`](results/analysis/) (steps 10–14). Figures F1–F6: [`F1`](results/figures/F1_overflow_by_tier.png), [`F2`](results/figures/F2_nurse_gap_by_tier.png), [`F3`](results/figures/F3_beds_over_time.png), [`F4`](results/figures/F4_nurses_vs_requirement.png), [`F5`](results/figures/F5_fairness_dispersion.png), [`F6`](results/figures/F6_checker_vs_audit.png) (`src/09_build_figures.py`). Animations of the net balance per department: [`R1`](results/figures/animations/R1_net_balances.gif), [`R2`](results/figures/animations/R2_net_balances.gif), [`R3`](results/figures/animations/R3_net_balances.gif) (`src/15_animations.py`). Run reports per run: [`results/evaluations/R1/run_report.json`](results/evaluations/R1/run_report.json) (likewise R2, R3, STRESS1). Baseline headroom: [`results/evaluations/headroom.json`](results/evaluations/headroom.json). Metric definitions and the pre-registered headline set: [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) §3 |
| **Reflection (30%)** | [`REFLECTION.md`](REFLECTION.md). Running record of errors and near misses: [`docs/REFLECTION_LOG.md`](docs/REFLECTION_LOG.md). Limitations: [`ANALYSIS.md` §5](ANALYSIS.md#5-limitations) (long working version: [`docs/LIMITATIONS_AND_REFLECTION.md`](docs/LIMITATIONS_AND_REFLECTION.md)). Error analysis: [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) |
| **Verification (20%)** | See the list below |

The Verification evidence, none of which depends on an LLM output:

- **Deterministic audit:** [`src/evaluation/audit.py`](src/evaluation/audit.py) re-implements the hard constraints, the nurse requirement and the bed-assignment replay independently of the environment. Per run: [`results/evaluations/R1/deterministic_audit.jsonl`](results/evaluations/R1/deterministic_audit.jsonl) (likewise R2, R3, STRESS1).
- **Headline numbers recomputed without the agent:** [`src/06_audit_and_metrics.py`](src/06_audit_and_metrics.py) recomputes the audit and the metrics from the run records alone and compares them with the committed audit (EQUAL for all four runs on 2026-11-23).
- **Data reconciliation:** `department_demand_daily` is checked against `patient_registry` (19 checks, [`src/data_generation/validation.py`](src/data_generation/validation.py); reports in [`data/processed/seed20261107/validation_report.json`](data/processed/seed20261107/validation_report.json) and the other datasets).
- **Frozen data:** [`data/MANIFEST.json`](data/MANIFEST.json), re-verified by [`src/01_verify_data.py`](src/01_verify_data.py).
- **Claim-by-claim verification of explanations:** [`src/evaluation/claim_check.py`](src/evaluation/claim_check.py), run by [`src/08_claim_verification.py`](src/08_claim_verification.py). Applied to R1: [`results/evaluations/R1/explanation_claims.json`](results/evaluations/R1/explanation_claims.json). The owner's review of the verdicts: [`results/evaluations/R1/owner_review/claim_accuracy_after_owner_review.json`](results/evaluations/R1/owner_review/claim_accuracy_after_owner_review.json); it and the other generated files of `owner_extraction/` and `owner_review/` are recomputed by the same script from the committed owner input tables and compared byte for byte.
- **CHECKER against the audit:** matching on (day, type), with recall, precision and level agreement: [`src/evaluation/checker_matching.py`](src/evaluation/checker_matching.py). The results are in each run report (`checker`, `checker_overall`).
- **Independent re-hashes of the runs:** [`tests/manual/verify_copy_back_independent.py`](tests/manual/verify_copy_back_independent.py) imports nothing from `src/`. Saved outputs (4 × OK) are in [`results/verification/copy_back/`](results/verification/copy_back/). **With only this repository, run `uv run python src/05_verify_copy_back.py`** (`--sums-only` mode). It re-hashes every file of each run against its `copy_back.json` and each subagent capture against its `SHA256SUMS.json`.
- **Run-session restrictions verified before the runs:** [`results/verification/pre_run/`](results/verification/pre_run/) (smoke test, run-settings probe).
- **Frozen run folders are read-only in code:** any write into a copied-back run raises an error ([`tests/test_frozen_guard.py`](tests/test_frozen_guard.py)).
- **Test suite:** [`tests/`](tests/).

**The brief's session outputs, and their equivalents here:**

| Brief | Here |
| --- | --- |
| The list of choices the agent made without asking you | Implementation Decisions Log, [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) §9 (the owner's decisions are in §11) |
| The same question re-run | R1, R2, R3: three independent agent runs on the same dataset with frozen prompts, in [`results/allocations/`](results/allocations/) |
| The headline number recomputed without the agent | Deterministic audit and metrics, [`src/06_audit_and_metrics.py`](src/06_audit_and_metrics.py) |
| Where the agent went wrong, and how you found out | Claim verification of R1 (above), CHECKER vs audit (above), [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) |
| Session record | [`docs/SESSION_LOG.md`](docs/SESSION_LOG.md) |

## 3. Repository map

```text
README.md  ANALYSIS.md  plan.md  ERROR_ANALYSIS.md  mistakes.md  REFLECTION.md   deliverables
CLAUDE.md                    standing instructions for the coding agent
.claude/agents/  .claude/run-settings.json  .mcp.json   agent definitions and run restrictions (frozen at prompts-v1.0)
data/                        the synthetic datasets (frozen at data-v1.0)
  raw/  metadata/  processed/  MANIFEST.json
src/                         code; 01_ … 16_ are the pipeline entry points
  data_generation/ environment/ mcp_server/ agent/ evaluation/ utils/
results/                     index: results/README.md
  allocations/  evaluations/ runs R1–R3, STRESS1 and baselines B0–B2 (records, audits, reports)
  analysis/                  analysis tables, HEADLINE_NUMBERS.csv
  figures/                   figures F1–F6; animations/ (one GIF per agent run)
  verification/              copy-back re-hashes, pre-run checks
  development/               dry runs and fixtures used to build and test the system
tests/                       automated tests; tests/manual/ holds checks that need the claude CLI or the run clone
docs/                        specification, evaluation plan, data dictionary, logs
```

- **`data/`, and the brief's *data/raw* and *data/derived*.** `data/raw/` holds the datasets exactly as generated and frozen. `data/processed/` plays the role of the brief's *data/derived*: validation reports and the Monte Carlo reference ranges. `data/metadata/` holds each dataset's configs. `data/` is not renamed or split because `data/MANIFEST.json`, frozen at tag `data-v1.0`, records these exact paths, and the hashed generator code writes them; any change would need a new data tag.
- **Why the runs stay under `results/allocations/` and `results/evaluations/`.** The four agent runs were copied back from the run clone with hash manifests and are frozen evidence: they are never moved or edited. All the evaluation code addresses runs as `results/{allocations,evaluations}/<run_id>/`. The index [`results/README.md`](results/README.md) groups them into runs, baselines, analysis, figures, verification and development.

## 4. AI assistance, data and privacy

**Disclosure of AI assistance.**

- **The system was implemented by Claude Code**, the coding agent (Claude Opus 5.5, per the `Co-Authored-By` line of every commit), under the instructions in [`CLAUDE.md`](CLAUDE.md). Its errors during development are part B of [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md).
- **The owner's reviews were prepared with an LLM advisor** (a separate claude.ai chat, without repository access) and relayed by the owner. The two cannot be separated in the record ([`docs/REFLECTION_LOG.md`](docs/REFLECTION_LOG.md) R52). This includes the owner verdicts on R1's wrong claims and the adjudication causes; the owner's own extraction of days 3, 8 and 18 is the part made without the advisor.
- **The system's agents** (dispatcher, ALLOCATOR, CHECKER) ran on the models below, from each run's `run_manifest.json` (`models`, checked per launch in `launches.jsonl`) and launch transcript:

  | Run | Dataset | Dispatcher, ALLOCATOR, CHECKER | Code (`prompts-v1.0`) | Claude Code |
  | --- | --- | --- | --- | --- |
  | R1 | `seed20261107` | `claude-sonnet-5-5` | `f2162c0` | 2.1.325 |
  | R2 | `seed20261107` | `claude-sonnet-5-5` | `f2162c0` | 2.1.328 |
  | R3 | `seed20261107` | `claude-sonnet-5-5` | `f2162c0` | 2.1.330 |
  | STRESS1 | `seed20261107_stress` | `claude-sonnet-5-5` | `f2162c0` | 2.1.330 |

- **LLM non-determinism:** a new agent run is a new run, never a reproduction. Differences between R1, R2 and R3 are part of the evaluation.

**Data, keys and privacy.**

- **Synthetic data, no personal data.** The four datasets are generated from fixed seeds by a stochastic simulation ([`src/data_generation/`](src/data_generation/)). A patient record holds only an ID, department, complexity level, arrival day and discharge day. The distributions are illustrative and are not real hospital statistics. Fields: [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).
- **No API key, token or paid API in the repository.** The agents run as Claude Code subagents against a local MCP server, on a Claude subscription; nothing in the code reads a key.
- **Local paths.** The frozen run records and transcripts contain local file paths, including the owner's Windows username. They are frozen evidence and are left unedited. In editable files, such paths are written as `~` or `<repo>`.

## 5. Reproduce

Requirements: Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/) (git only for a clone). Get the code either way:

- **Clone:** `git clone <repository URL> C:\hra` (any short folder), then `cd C:\hra`.
- **Zip:** unzip into a short folder (for example `C:\hra\`) and open a shell there. The zip is built with `git archive`, so it holds exactly the committed bytes and no `.git`. Everything below runs from it; the tests that read the committed version of a file through git (`tests/test_owner_inputs.py`) skip with the reason "needs a git checkout".

Then, in the repository root:

```bash
uv sync                                         # environment
uv run pytest -q                                # fast test suite; full suite: uv run pytest -q -m "slow or not slow"
uv run python src/01_verify_data.py             # data manifest ("manifest OK"); --regenerate rebuilds all datasets byte for byte
uv run python src/02_montecarlo.py              # optional, slow: Monte Carlo reference ranges, compared with the committed ones
uv run python src/03_run_baselines.py           # baselines B0–B2 on the four datasets, compared with the committed ones
uv run python src/04_agent_run.py               # prints the agent-run commands only: agent runs are not re-runnable (needs the claude CLI)
uv run python src/05_verify_copy_back.py        # re-hash the four agent runs against their copy-back manifests
uv run python src/06_audit_and_metrics.py       # audit and metrics of R1–R3 and STRESS1 recomputed without the agent
uv run python src/07_run_reports.py             # run reports and CHECKER-vs-audit matching, rebuilt
uv run python src/08_claim_verification.py      # R1's explanation claims re-verified, then the owner review recomputed (recall, adjudication, accuracy), byte for byte
uv run python src/09_build_figures.py           # figures F1–F6 into results/figures/ (after steps 10–13)
uv run python src/10_main_comparison.py         # R1–R3 vs B0–B2: gate D, A1–A3, secondaries, variability (results/analysis/)
uv run python src/11_checker_vs_audit.py        # the CHECKER against the audit, R1–R3, stratified
uv run python src/12_checker_on_wrong_claims.py # the CHECKER on R1's wrong explanation claims (75 primary, 19 descriptive)
uv run python src/13_stress1.py                 # the STRESS1 probe, incl. the shock-day closed-form test
uv run python src/14_write_analysis.py          # ANALYSIS.md and HEADLINE_NUMBERS.csv from the tables (--check: up to date?)
uv run python src/15_animations.py             # one GIF per agent run: net balance per department and day
uv run python src/16_error_analysis.py         # ERROR_ANALYSIS.md, its tables and ERROR_NUMBERS.csv (--check: up to date?)
```

- Steps 10–14 write the committed analysis tables in `results/analysis/`; re-running them reproduces the files byte for byte. Other recomputations go to `results/analysis/recomputed/` (ignored by git). Each script reports EQUAL or DIFFERENT against the committed file, ignoring timestamps. No script writes into the frozen run folders.
- **Windows and long paths.** The longest path in the repository is 132 characters, so a clone or unzip under a short folder (for example `C:\hra\`) works as is. Under a deep folder, paths can exceed Windows' 260-character limit. In that case, run `git config --global core.longpaths true` before cloning (it is a git setting and does not travel with a clone), or enable `LongPathsEnabled` (administrator; `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem`). The project's own readers handle long paths in any case.
- Line endings are fixed by [`.gitattributes`](.gitattributes), so the frozen data and transcripts keep their committed bytes on checkout.

## 6. What's in `docs/`

Supporting material behind the deliverables. The standing instructions for the coding agent are in [`CLAUDE.md`](CLAUDE.md) at the root.

| File | What it is for |
| --- | --- |
| [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) | Specification: technical design, Implementation Decisions Log (§9) and owner decisions (§11) |
| [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) | Pre-registered metrics and evaluation protocol: baselines, run plan, verification checks |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Description of the data: dataset fields and validation checks |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Specification of the system's agents: roles, tools, workflow, state |
| [`docs/REFLECTION_LOG.md`](docs/REFLECTION_LOG.md) | Running error log, written when each error happened; source of [`ERROR_ANALYSIS.md`](ERROR_ANALYSIS.md) part B |
| [`docs/SESSION_LOG.md`](docs/SESSION_LOG.md) | Log of the work sessions: one entry per session |
| [`docs/CLEANUP_PLAN.md`](docs/CLEANUP_PLAN.md) | Repository clean-up and publication scan; §10 maps the two moved paths cited in `EVALUATION_PLAN.md` |
| [`docs/LIMITATIONS_AND_REFLECTION.md`](docs/LIMITATIONS_AND_REFLECTION.md) | Long working version behind the Limitations ([`ANALYSIS.md` §5](ANALYSIS.md#5-limitations)) and [`REFLECTION.md`](REFLECTION.md) |
