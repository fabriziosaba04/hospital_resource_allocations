# Agents: Architecture and Workflow

This document specifies the multi-agent architecture of the Hospital Resource Allocation Agent: the four logical agents, their implementation, tools, responsibilities, inputs and outputs, execution order, state management and validation workflow.

It is subordinate to [`CLAUDE.md`](../CLAUDE.md), which defines the project's scope, decision principles, hard constraints and data model. This document does not restate those principles; it assigns responsibility for applying and enforcing them. If the two documents ever appear to conflict, `CLAUDE.md` prevails and the conflict must be raised with the project owner.

Record schemas, prompt templates, numerical parameters and thresholds are not defined here. Items still undecided are listed in [Section 12](#12-open-items). The design decisions were last updated on 2026-11-12 (severity scale, §6); the run-session deny rules in §2.3 date from 2026-11-11.

## 1. Architecture Overview

The system consists of four logical agents:

| Agent | Role | Implementation | Runs | Writes |
| --- | --- | --- | --- | --- |
| **ANALYZER** | Understands the current operational situation | Deterministic function `run_analyzer` inside the server | Every simulated day | Observed State |
| **ALLOCATOR** | Makes resource allocation decisions | LLM, as a Claude Code subagent using tools | Every simulated day | Allocation State, Decision History |
| **CHECKER** | Independently audits recent decisions | Deterministic audit component inside the server, plus an LLM Claude Code subagent | Every five simulated days | Deterministic Audit Record (deterministic component), Validation History (LLM) |
| **ORCHESTRATOR** | Coordinates and enforces the workflow | Deterministic state machine inside the server; in run sessions, the main Claude Code session runs as the restricted `dispatcher` agent | Every simulated day | Workflow records |

The server also contains a deterministic **environment component**, which is not an agent. It applies pre-declared rules fixed before the run, involving no judgement:

- The common initial allocation.
- The intra-department bed assignment rule (`CLAUDE.md` §10.F).
- The hard-constraint validator.
- The what-if computation.
- The failure repair rule (Section 10).

Roles, instructions, inputs, outputs and responsibilities remain separate. One agent must never perform another agent's role.

Core separation:

- **Observing is separate from deciding:** the ANALYZER interprets facts, the ALLOCATOR decides.
- **Deciding is separate from auditing:** the CHECKER evaluates the ALLOCATOR independently.
- **Coordinating is separate from all three:** the ORCHESTRATOR runs the workflow but makes no allocation decisions.

## 2. Implementation and Enforcement

The course instructor requires LLM agents to operate through **explicit tool calls**. Rules in this document are therefore enforced by code and permissions, not only by instructions.

### 2.1 One server instance per role

- The server is **local Python code** in `src/mcp_server/`, managed with `uv` and using stdio transport. The deterministic rules it shares with the baselines live in `src/environment/`. There are no external services and no paid APIs.
- The same server code runs as **one instance per role**, each exposing only that role's tools.
- Instances coordinate **only through the persistent records on disk**, including the state-machine state.
- The exact tool signatures, state machine and storage are specified in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

| Instance | Used by | Configured in | Exposes |
| --- | --- | --- | --- |
| **Orchestration** | Main session (dispatcher) | `.mcp.json` | Workflow-only tools: `advance_day`, `end_allocation_phase`, `close_day`, `get_workflow_status`. No submit tools and no data tools. |
| **ALLOCATOR role** | ALLOCATOR subagent | Inline in `.claude/agents/allocator.md` (`mcpServers` field) | ALLOCATOR tools (Section 5) |
| **CHECKER role** | CHECKER subagent | Inline in `.claude/agents/checker.md` (`mcpServers` field) | CHECKER tools (Section 6) |

### 2.2 Documented Claude Code behaviour

Verified against the Claude Code documentation on 2026-11-07.

| Topic | Documented behaviour | Consequence |
| --- | --- | --- |
| **Inline `mcpServers`** | Inline servers are "connected when the subagent starts … and disconnected when it finishes". To keep a server out of the main conversation, "define it inline here rather than in `.mcp.json`. The subagent gets the tools; the parent conversation doesn't." Inline definitions use the same schema as `.mcp.json` entries. | The role servers are defined only inline. They never appear in `.mcp.json`, so the main session cannot call `submit_decision` or `submit_validation_report`. |
| **Folder trust** | Inline servers in project `.claude/agents/` files load only after the project folder is trusted. Until then they are skipped. | The project folder must be trusted before a run. The smoke test detects a skipped server. |
| **`tools` field** | Comma-separated or YAML list. If omitted, the subagent **inherits every available tool**, including the main session's orchestration tools. | Each subagent must set `tools` to its own role tools only, so it cannot call `advance_day` or `close_day`. It must also have no Write, Edit, Bash or Agent access, so it cannot spawn subagents. |
| **MCP tool names** | `mcp__<server>__<tool>` names one tool, and `mcp__<server>__*` names all tools of a server. | Server names must avoid `.`, spaces, `__` and a trailing `_`. |
| **Unknown fields** | Unrecognised frontmatter fields are ignored silently. | Field names must match the documentation exactly. |
| **`omitClaudeMd`** | Custom subagents load `CLAUDE.md` by default. `omitClaudeMd: true` starts a subagent without it. The field is ignored for an agent running as the main session. | `allocator.md` and `checker.md` set `omitClaudeMd: true` (approved 2026-11-07), so they cannot learn the generator design. Their prompts restate the principles they need, consistent with `CLAUDE.md` and reviewed by the owner before the first run. |
| **`.mcp.json` approval** | Project-scoped servers require approval in interactive sessions. | The orchestration server must be approved once. |
| **`--agent` main session** | `--agent <name>` makes the main thread "take on that subagent's tool restrictions and model". `CLAUDE.md` still loads. | In run sessions, the dispatcher is started with `--agent dispatcher`, so its `tools` field bounds what the main session can do. |
| **`Agent(type, …)` allowlist** | In the `tools` field of an agent running as the main thread, `Agent(worker, researcher)` restricts which subagents can be spawned. It is ignored inside subagent definitions. | The dispatcher's `tools` field is `mcp__orchestration__*` plus `Agent(allocator, checker)`, and nothing else. |
| **`--settings <file>`** | Applies a settings file to one session, overriding the same keys in the other settings files. | Run-only deny rules live in `.claude/run-settings.json`, so they never affect development sessions. |
| **`Read` deny rules** | `Read(./path/**)` blocks Claude's file-reading tools, including Grep and Glob, on a path. | Run settings deny reading hidden and raw data. Server processes are unaffected, because they are Python, not Claude tools. |

### 2.3 How rules are enforced

| Rule | Enforcement |
| --- | --- |
| **One writer per record** | Each submit tool exists only in its role's server instance. Deterministic records are written only by their server component. |
| **Temporal rule** | The current day lives in the state-machine record and is never a tool parameter. Tools never return post-day-t data, and never return `discharge_day` for present patients. |
| **Hidden generation parameters** | No tool reads `generation_config`. Agents see only `max_beds` and the nurse weights w(L1–L3). |
| **Hard constraints** | `submit_decision` runs the hard-constraint validator and records the outcome. |
| **Execution order** | The state machine rejects out-of-order calls from any instance. |
| **Dispatcher neutrality (run sessions)** | The main session runs as the `dispatcher` agent: only orchestration tools and the two subagents, no Read, Write, Edit or Bash. Run-only deny rules cover all of `data/**` (deny-by-default, so agents reach data only through the server), plus `docs/` and the generator code, which contain the generation parameters. The run session must start from the project root, because the rules use `./` paths. Dispatch prompts are fixed templates that carry no data. |

### 2.4 Smoke test (required before any run)

The smoke test must show that:

1. The ALLOCATOR subagent can call exactly its whitelisted tools, and cannot call CHECKER or orchestration tools.
2. The CHECKER subagent can call exactly its whitelisted tools, and cannot call ALLOCATOR or orchestration tools.
3. The main session cannot call `submit_decision` or `submit_validation_report`.
4. Both inline role servers actually connect, so the folder is trusted.
5. In a run session, the dispatcher:
   - cannot read files under the denied paths;
   - cannot use Write, Edit or Bash;
   - cannot spawn any subagent other than `allocator` and `checker`.

If one-instance-per-role proves infeasible, the fallback is to accept the gap and declare it as a limitation in `docs/LIMITATIONS_AND_REFLECTION.md`, but only after reporting to the project owner.

### 2.5 Execution mode

- The agents run as Claude Code subagents. No API key is used.
- Only 1–3 agent runs are expected. LLM non-determinism must be declared, and differences between runs are material for the Reflection.
- All state lives in persistent records, so a run can be resumed from any day. This also mitigates context compaction in long sessions.

## 3. State and Records

Each record has exactly one writer, with two declared exceptions in the Allocation State, explained below the table.

| Record | Content | Written by | Read by |
| --- | --- | --- | --- |
| **Observed State** | What is observed in the simulated hospital on each day, including External Changes | ANALYZER | ALLOCATOR, CHECKER |
| **Allocation State** | B_d(t) and N_d(t) for each department and day, each entry attributed to its source | ALLOCATOR (via `submit_decision`); see the exceptions below | ANALYZER, ALLOCATOR, CHECKER, environment |
| **Decision History** | Each decision with its reasoning, alternatives considered, expected consequences, and every submission attempt with its validation outcome | ALLOCATOR (via `submit_decision`) | ALLOCATOR, CHECKER |
| **Bed Assignment State** | Per patient and per day: in a bed or in overflow, and in which department | Environment component | ALLOCATOR (current day only, via `get_overflow_queue`), deterministic audit, metrics |
| **Deterministic Audit Record** | Hard-constraint checks, clinical priority violations and their severity, and metrics for each audit period | CHECKER deterministic component | LLM CHECKER, final evaluation |
| **Validation History** | The LLM CHECKER's validation reports, and recorded failures of the LLM layer | LLM CHECKER (via `submit_validation_report`); failures recorded by the ORCHESTRATOR | Final evaluation only. The ALLOCATOR does **not** read it in the main run. |
| **Workflow records** | Which steps ran on which day, in what order, with what outcome, plus failures, repairs and halts | ORCHESTRATOR | Final evaluation |

**Declared exceptions in the Allocation State.** Two entry types are not written by the ALLOCATOR. Both are attributed to their rule, never to the ALLOCATOR:

1. **The initial allocation**, written by the common initial-allocation rule (`CLAUDE.md` §10.L).
2. **A repaired allocation**, written by the deterministic repair rule after a failed decision (Section 10).

**External Changes** are changes in the hospital-level pools P_B(t) and P_N(t) that are not caused by the ALLOCATOR. Shocks never target a specific department. The ANALYZER identifies them and records them as part of the Observed State.

### 3.1 Data provenance rules

- **Original datasets are immutable.** No agent or server component modifies the input tables described in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).
- **Observed facts and agent decisions are never mixed.** The datasets contain only hospital-level pools. Department-level allocations exist only in the Allocation State.
- **History is preserved.** Records for past days are not overwritten. A new day produces new records rather than altering earlier ones.
- **Every record is attributable.** It must be possible to tell which agent or rule produced a record, for which simulated day, and from which inputs.
- **State is explicit and persistent.** Hospital conditions and previous decisions must be recoverable from structured records, never from a model's conversational memory.

### 3.2 Information rules

On day t, each agent may only use information available up to day t. Future information must never influence decisions.

- The current day is held in the state-machine record. No tool takes a day as an input for current-state queries.
- Tools never return post-day-t data.
- Tools never expose the `discharge_day` of patients still present. A discharge is observed only on the day it happens.
- Agents never see the true generation parameters (`generation_config`). They see only `max_beds` and the nurse weights.

## 4. ANALYZER

### Purpose

Understand and record the operational situation on day t. **It does not make resource allocation decisions.**

### Implementation

- The deterministic function `run_analyzer`, run by the orchestration instance as part of `advance_day`. It is not a subagent.
- An optional LLM narrative summary of the day's situation is allowed but not required. If one is produced, it must not replace or alter the deterministic Observed State.

### Inputs

- The rows of the input tables available on day t, never `generation_config`.
- The previous recorded Observed State.
- The previous Allocation State and Bed Assignment State (read-only), needed to identify imbalances and potential shortages.

### Responsibilities

- Compare current observations with the previous state.
- Identify arrivals, discharges and census changes by department and complexity level.
- Identify External Changes in the hospital-level pools, and whether they make the current allocation infeasible.
- Identify imbalances and potential shortages, including emerging trends such as a department surge.
- Write the Observed State for day t.

### May modify

- The Observed State for day t only.

### Must not

- Make, recommend or imply allocation decisions.
- Modify any other record.
- Overwrite observations recorded for earlier days.
- Treat the current Allocation State as an observation, or an observation as an allocation decision.
- Use information from after day t.

## 5. ALLOCATOR

### Purpose

Decide B_d(t) and N_d(t) for the four departments on day t. The ALLOCATOR assigns beds to **departments, not to patients**. Patient-level bed assignment follows the deterministic rule in `CLAUDE.md` §10.F.

### Implementation

An LLM Claude Code subagent (`.claude/agents/allocator.md`, planned), connected to the ALLOCATOR role server and whitelisted to these tools only:

| Tool | Type | Purpose |
| --- | --- | --- |
| `get_observed_state` | Read | The Observed State for day t |
| `get_allocation_state` | Read | The current Allocation State |
| `get_decision_history` | Read | Previous decisions and their reasoning |
| `get_overflow_queue` | Read | Current day only: `patient_id`, `department`, `complexity`, `arrival_day` and days waiting for every patient in overflow. It **never returns `discharge_day`**. |
| `simulate_allocation` | What-if | For a proposed allocation, the resulting overflow, nurse shortages and clinical priority violations, **on day t only** |
| `validate_allocation` | Check | Runs the hard-constraint validator without submitting |
| `submit_decision` | **Write** | Submits the decision and its reasoning. The hard-constraint validator runs, and the attempt and its outcome are recorded. |

`simulate_allocation` does not project into the future. Any anticipation by the ALLOCATOR must come from the history it can read.

### Inputs

- The Observed State for day t.
- The current Allocation State.
- The Decision History.
- The current overflow queue.
- Not the Validation History, in the main run.

### Responsibilities

- Read the Observed State produced by the ANALYZER.
- Consider current resource availability, demand, clinical priorities and previous allocation decisions.
- Infer demand patterns from history. This is part of the adaptive role, since the generation parameters are hidden.
- Evaluate whether the existing allocation should be maintained or modified, using `simulate_allocation` to compare alternatives.
- Decide how beds and nurses are allocated across departments, treating the two resources as distinct categories.
- Respect the hard constraints in `CLAUDE.md` §10.E, including no-eviction and its relaxation under shocks.
- Apply the fairness criterion F1 (`CLAUDE.md` §10.H), with waiting measured from `arrival_day`, as a guide when choosing among clinically acceptable alternatives.
- Submit the decision with its reasoning.

The ALLOCATOR makes exactly **one accepted allocation decision per simulated day**. Maintaining the existing allocation is a valid decision and must be submitted and explained like any other.

On day 1, the existing allocation is the common initial allocation, with beds already assigned to present patients by the intra-department rule.

### Decision hierarchy

1. **Clinical priority (non-negotiable).** It is never sacrificed to improve fairness or efficiency.
2. **Fairness.** It is preferred over efficiency when clinically acceptable alternatives exist.
3. **Efficiency.** It is optimized subject to the two principles above.

### Daily responsibility for constraints

**The ALLOCATOR is responsible for respecting all constraints every day.** Validation at submission rejects hard-constraint violations, but it does not check clinical priority, fairness or efficiency. The CHECKER audits only every five days. Neither reduces the ALLOCATOR's own responsibility.

### Decision record

Each submitted decision must cover the explanation requirements in `CLAUDE.md` §3.6:

- The situation and problem detected.
- The relevant information used.
- The alternatives considered.
- The reasons for the selected allocation.
- The expected benefits and trade-offs, including any fairness–efficiency trade-off.
- Any relevant uncertainty or limitation.

### May modify

- The Allocation State for day t and the Decision History, only through `submit_decision`.

### Must not

- Modify any other record or the original datasets.
- Alter or delete earlier decision records.
- Use information from after day t.
- Base priority on department membership instead of individual clinical complexity.

## 6. CHECKER

### Purpose

Independently audit the ALLOCATOR's decisions and document where the system made mistakes, why they occurred and what their consequences were.

### Schedule

The CHECKER runs on every simulated day t with t mod 5 = 0. Each audit covers all decisions made since the previous audit.

### Two layers

| Layer | Implementation | Checks | Output |
| --- | --- | --- | --- |
| **Deterministic audit** | Server component, triggered by the state machine on every audit day. It **always runs**. | Hard constraints, clinical priority violations and their severity (`CLAUDE.md` §10.G), and metrics | Deterministic Audit Record |
| **LLM review** | Claude Code subagent (`.claude/agents/checker.md`, planned), connected to the CHECKER role server | Whether the ALLOCATOR's explanations are accurate and consistent with the data, and inconsistencies between consecutive decisions | Validation History |

- **The deterministic audit is the independent verification.** It must not depend on any LLM output. It runs and is recorded before the LLM layer is invoked.
- Only the LLM layer can fail. A failure is recorded in the Validation History and the workflow continues.
- The same deterministic audit is applied to the baselines.

### LLM CHECKER tools

| Tool | Type | Purpose |
| --- | --- | --- |
| `get_deterministic_audit(period)` | Read | The Deterministic Audit Record for the period, already produced by the server |
| `get_decision_history(period)` | Read | The ALLOCATOR's decisions and reasoning |
| `get_observed_state(period)` | Read | Observations for the period |
| `submit_validation_report` | **Write** | Submits the report to the Validation History |

`period` may only cover days up to the current day.

### Independence

- The CHECKER assesses decisions using the underlying records, rather than simply accepting the ALLOCATOR's explanations. It reads the explanations to judge whether they are accurate, not as evidence that a decision was correct.
- **A convincing explanation is not proof of a correct decision.**
- When judging whether a decision was correct, the CHECKER considers what was knowable on the day it was made. Later observations may describe a decision's actual consequences, but must not fault a decision for failing to anticipate unavailable information.

### Issue reporting

Each identified issue should include, where applicable:

- What happened.
- What should have happened.
- Why the decision was incorrect.
- The relevant principle or constraint.
- The potential or actual impact.
- Severity.
- A suggested corrective action.

The severity of a clinical priority violation is the level difference defined in `CLAUDE.md` §10.G. The general severity scale (Critical, Major, Moderate, Minor), the test separating violations, concerns and improvements, and the mapping of every issue type were fixed on 2026-11-12 and are in [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §4. Calls to `validate_allocation` are free and never counted; only rejected submissions are issues. The LLM CHECKER uses the same scale, and its issues are matched against the deterministic audit's (recall, precision, level agreement) as a primary Verification output.

Reports must distinguish **actual constraint violations** from less severe **concerns** and **opportunities for improvement**.

An audit that finds no issues must still produce a report stating what was checked.

### May modify

- Deterministic component: the Deterministic Audit Record, by adding records only.
- LLM layer: the Validation History, by adding reports only.

### Must not

- Modify allocation decisions, the Allocation State, the Bed Assignment State, the Observed State or the Decision History.
- Block or halt the workflow. Its findings are recorded, not enforced.
- Rewrite or delete earlier audit records or reports.

## 7. ORCHESTRATOR

### Purpose

Coordinate and enforce the workflow. **The ORCHESTRATOR is the coordinator, not the decision-maker.**

### Implementation

- **The state machine**, held in the persistent state-machine record and respected by every server instance, enforces the daily cycle, holds the current day, controls data access, records workflow events and rejects out-of-order calls.
- **The main Claude Code session** is only a dispatcher, connected only to the orchestration instance:
  - It calls the workflow tools and invokes the subagents in the order the state machine requires.
  - It cannot submit decisions or reports.
  - It exercises no judgement over allocations or reports.
- **In run sessions, the dispatcher runs as the restricted `dispatcher` agent** (Section 2.3), and its prompts to subagents are fixed templates with no data.
- **Development sessions** are unrestricted and must never be used to execute a run (`CLAUDE.md` §9.1).

### Responsibilities

- Manage the daily execution cycle and the current simulated day.
- Run the ANALYZER as part of `advance_day`.
- Accept the ALLOCATOR's submissions only in the allocation phase, and apply the failure handling in Section 10.
- On audit days, trigger the deterministic audit, then enable the LLM CHECKER phase.
- Record each step, failure, repair and completed daily cycle.

### May modify

- Workflow records, and the recording of LLM CHECKER failures.

### Must not

- Make, alter or override resource allocation decisions, or apply any rule not declared before the run.
- Replace or reinterpret the reasoning of the other agents.
- Modify the contents of any other record.
- Give any agent access to information from after the current simulated day.

## 8. Daily Execution Sequence

```text
advance_day ─▶ ANALYZER ─▶ ALLOCATOR ─▶ [bed assignment] ─▶ CHECKER (only if t mod 5 = 0) ─▶ close_day
```

For each simulated day t:

1. **Start of day.** The dispatcher calls `advance_day`. The state machine moves to day t, and `run_analyzer` writes the Observed State.
2. **Decision.** The dispatcher invokes the ALLOCATOR subagent. The subagent reads the state, explores alternatives and calls `submit_decision`.
3. **Validation.** The server validates the submission against the hard constraints. On rejection, the ALLOCATOR may retry, up to N attempts.
4. **End of the allocation phase.** The dispatcher calls `end_allocation_phase`.
   - If no decision was accepted, the repair rule is applied and the failure is recorded (Section 10).
   - The environment component then writes the Bed Assignment State for day t.
5. **Audit (only if t mod 5 = 0).**
   - `end_allocation_phase` also runs the deterministic audit, which writes the Deterministic Audit Record.
   - The dispatcher then invokes the CHECKER subagent, which calls `submit_validation_report`.
6. **End of day.** The dispatcher calls `close_day`.
   - On an audit day with no LLM report, `close_day` records the LLM-layer failure. It never blocks.
   - The state machine records the completed cycle.

**Out-of-order calls are rejected**, for example:

- `submit_decision` outside the allocation phase.
- `submit_validation_report` outside the audit phase.
- `close_day` before `end_allocation_phase`.
- `advance_day` before `close_day`.

**Day 1:**

1. Before the ALLOCATOR acts, the environment component applies the common initial allocation (`CLAUDE.md` §10.L).
2. It assigns beds to the patients present after burn-in, using the intra-department rule.
3. The ALLOCATOR then maintains or modifies the allocation, as on any other day. No-eviction protects the patients assigned in step 2.

**Within-day timing (confirmed):** discharges → arrivals → observation → allocation → bed assignment.

### Example: 30-day simulation

| Step | Executions | Days |
| --- | --- | --- |
| Daily cycles (ORCHESTRATOR) | 30 | 1–30 |
| ANALYZER | 30 | 1–30 |
| ALLOCATOR (accepted decisions or repairs) | 30 | 1–30 |
| Deterministic audit | 6 | 5, 10, 15, 20, 25, 30 |
| LLM CHECKER (reports or recorded failures) | 6 | 5, 10, 15, 20, 25, 30 |

The horizon is H = 30 (approved 2026-11-07), a multiple of 5, so partial audits do not arise.

## 9. Five-Day Audit Cycle

- Audit k covers every decision made after the previous audit, up to and including the current day. Every daily decision is audited exactly once.
- The audit runs after that day's allocation has taken effect, so the current day is included.
- The audit is retrospective and does not alter the following day's cycle.
- Audits are **purely retrospective** in the main run: the ALLOCATOR does not read validation reports. A feedback run may be added later as an ablation.
- The five-day frequency is **not** permission for the ALLOCATOR to violate constraints on other days.

## 10. Validation and Failure Handling

| Level | Who | What | When |
| --- | --- | --- | --- |
| **Submission validation** | Environment component, inside `submit_decision` | Hard constraints: conservation, bounds and integrality, no-eviction and its relaxation under shocks (`CLAUDE.md` §10.E) | Every submission |
| **Workflow validation** | ORCHESTRATOR state machine | Correct order, correct day, completeness of records | Every step |
| **Decision audit** | CHECKER | Clinical priority, fairness, efficiency, feasibility and consistency over time | Every five days |

### When `submit_decision` is rejected

1. The ALLOCATOR receives the rejection reasons and retries, up to N = 3 attempts (approved 2026-11-07). Every attempt is recorded.
2. If no decision is accepted, a **pre-declared deterministic repair rule** adapts the previous allocation to the current pools. Δ is the change in a pool since the previous day.
   - **Nurses:** Δ is spread in proportion to the previous N_d, using largest remainder.
   - **Beds, Δ > 0:** the new beds are split in proportion to the previous B_d, within the cap.
   - **Beds, Δ < 0:** free beds are removed first. Then occupied beds are cut hospital-wide, lowest level first, then most recent `arrival_day`, then `patient_id`.
3. The repaired allocation is **attributed to the repair rule, not to the ALLOCATOR**. It is recorded as an ALLOCATOR failure in the evaluation.
4. The run **halts only if repair is impossible**, with a recorded reason. The bed-cap generation constraint (`CLAUDE.md` §4) rules this out in practice.

The exact algorithm, including residual tie-breaks, is in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).

**Why repair does not breach the ORCHESTRATOR's neutrality.** The repair rule is declared before the run, is fully deterministic and involves no judgement by the ORCHESTRATOR. It is therefore not an invented allocation, but a fixed environment rule, like the initial allocation and the bed assignment rule.

Rules:

- No component produces an allocation outside the ALLOCATOR's accepted decisions and the pre-declared rules.
- A failure is never silently ignored.
- CHECKER findings never block the workflow. Only the LLM CHECKER can fail, and its failure is recorded.

## 11. Interaction Rules

- Agents interact only through server tools and persistent records, never through implicit conversational memory.
- Each record has exactly one writer (Section 3), enforced by the role server instances and tool whitelists.
- The dispatcher invokes every subagent. Subagents do not invoke each other.
- The ALLOCATOR acts on the ANALYZER's recorded Observed State, not on its own reinterpretation of raw data.
- The CHECKER reads the ALLOCATOR's records but forms its own judgement (Section 6).

### Logging and traceability

The records must make it possible to reconstruct, for any simulated day:

- Which steps ran, in what order, and with what outcome.
- What was observed, including any External Changes.
- What allocation was in place before and after the decision, which transfers of beds and nurses took place, and who produced the allocation (ALLOCATOR, initial rule or repair rule).
- Which patients were in a bed or in overflow.
- Every submission attempt and its validation result.
- Why the ALLOCATOR made its decision, and which alternatives it considered.
- Which audit covered the decision, and what the deterministic and LLM layers found.

The records must also identify the run and the input datasets they relate to, so that results can be reproduced and compared with the baselines.

The dynamic visualization must be built from these records. It may only show resource movements that actually appear in the Allocation State.

## 12. Open Items

No agent-architecture items are open. The severity scale was fixed on 2026-11-12 (`EVALUATION_PLAN.md` §4).

Implementation-level choices are recorded in the Implementation Decisions Log in [`PROJECT_SPEC.md`](PROJECT_SPEC.md). They cover workflow tools, record formats, storage, LLM CHECKER failure handling, tie-breaks and code layout.
