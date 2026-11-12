# Hospital Resource Allocation Agent

This is the main reference for Claude Code sessions on this project. It records the project's identity, scope, decision principles, constraints and working expectations.

The multi-agent architecture (agent roles, implementation, tools, inputs and outputs, execution order, state management and validation workflow) is specified in [`docs/AGENTS.md`](docs/AGENTS.md). Dataset fields are specified in [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

Agreed conceptual decisions and the items that remain open are listed in [Section 10](#10-conceptual-decisions-and-open-items). **The conceptual design was frozen on 2026-11-07** (Section 9).

Other project documents:

| Document | Content |
| --- | --- |
| [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) | Consolidated technical design and the Implementation Decisions Log |
| [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) | Metrics, baselines, run plan and verification |
| [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | Summary for new readers |
| [`docs/REFLECTION_LOG.md`](docs/REFLECTION_LOG.md) | Running record of errors and near misses, for the Reflection and Verification sections |

## 0. Project Structure

Entries marked *(planned)* are approved but not yet created.

```text
hospital_resource_allocations/
│
├── README.md
├── CLAUDE.md
├── pyproject.toml                 uv project (dependencies, pytest config)
├── uv.lock
├── .gitignore
├── .gitattributes                 keeps data and configs byte-exact (no line-ending conversion)
├── .mcp.json                      (planned) orchestration server only (main session)
│
├── .claude/
│   ├── run-settings.json          deny rules for run sessions only
│   └── agents/                    (planned) agent definitions
│       ├── dispatcher.md          (planned) restricted main session for runs (--agent)
│       ├── allocator.md           (planned) defines the ALLOCATOR role server inline
│       └── checker.md             (planned) defines the CHECKER role server inline
│
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   ├── PROJECT_SPEC.md
│   ├── DATA_DICTIONARY.md
│   ├── AGENTS.md
│   ├── EVALUATION_PLAN.md
│   ├── LIMITATIONS_AND_REFLECTION.md
│   └── REFLECTION_LOG.md          running record of errors and near misses
│
├── data/
│   ├── MANIFEST.json              SHA-256 of every frozen data file (tag data-v1.0)
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── src/
│   ├── data_generation/           stochastic generator, data validation, statistics, Monte Carlo
│   │   └── configs/               template generation and environment configs
│   ├── environment/               deterministic rules shared by server and baselines (cut path built; rest planned)
│   ├── mcp_server/                (planned) MCP tool layer, state machine, role instances
│   ├── agent/                     agent prompts and dispatch templates
│   ├── evaluation/                deterministic audit, metrics, baselines
│   └── utils/
│
├── results/
│   ├── allocations/
│   ├── evaluations/
│   └── visualizations/
│
├── tests/
│   └── manual/                    checks that need the claude CLI (run-settings verification)
│
└── notebooks/
```

Keep this tree up to date when files or directories are added, moved or removed. Do not change the structure without the project owner's approval.

## 1. Project Identity

The project develops an intelligent decision-support agent for hospital resource allocation. The agent analyses hospital conditions, identifies allocation imbalances, evaluates alternative allocation strategies, and provides transparent, evidence-based recommendations.

It combines analytical reasoning, mathematical optimization and operational assessment to balance clinical needs, fairness and resource efficiency.

Its core identity is an **Agent as a Decision-Making System**, with selected capabilities of an adaptive operations manager. Through lightweight adaptive monitoring, it processes new information about hospital conditions, identifies relevant changes and reassesses earlier allocation decisions when necessary.

The agent is not intended to manage a real hospital autonomously or to replace human decision-makers.

## 2. Scope

The prototype operates in a controlled, simulated hospital environment. The scope below is deliberately limited.

| Element | Definition |
| --- | --- |
| Departments | Exactly four: Internal Medicine, Cardiology, Neurology, Orthopedics |
| Resources | Exactly two: beds and nursing staff (nurses) |
| Clinical complexity | Three levels: Level 3 is the highest clinical priority, Level 1 the lowest |
| Patient attributes | Unique patient ID, department, clinical complexity level, arrival day, discharge day (minimal by design; see Section 10.C) |

Beds and nurses are distinct categories, with separate allocation decisions and constraints.

Do not add departments, resource categories or unnecessary operational complexity without explicit approval from the project owner.

## 3. Decision-Making Principles

The agent follows a clear hierarchy of objectives: **clinical priority, then fairness, then efficiency**. Operational feasibility and the ethical constraints apply to every decision.

### 3.1 Clinical priority (non-negotiable)

- Individual patient clinical priority is the primary consideration: Level 3 > Level 2 > Level 1.
- This holds regardless of department.
- A decision must never sacrifice higher-priority clinical needs to improve fairness or efficiency.
- The operational definition of a clinical priority violation is in Section 10.G.

### 3.2 Fairness (high priority)

- Fairness is a fundamental objective, not merely a secondary performance indicator.
- The agent promotes equitable access to resources among patients with comparable clinical needs, meaning the same complexity level (Section 10.H).
- Among clinically acceptable alternatives, it should generally prefer the more equitable one, even at a moderate cost in operational efficiency.
- Fairness and efficiency trade-offs must be explicitly identified and explained.

### 3.3 Efficiency (optimization objective)

- The agent aims to use beds and nurses efficiently, minimizing unnecessary underutilization and resource imbalances.
- Efficiency is always subordinate to clinical priority and must be balanced against fairness.

### 3.4 Department-specific characteristics

- The four departments must have different operational profiles. They differ **only** in clinical complexity mix and patient arrival rate (Section 10.B).
- Length of stay and nursing requirements depend on clinical complexity level only, and are the same across departments.
- No absolute priority ranking between departments has been established.
- A patient's priority depends primarily on individual clinical complexity, not on their department.
- Department characteristics should influence resource requirements and allocation decisions without creating an arbitrary hierarchy between departments.

### 3.5 Operational feasibility

Every allocation must respect the available resources and the constraints defined for the environment. The agent must:

- Never create resources artificially.
- Respect department capacity constraints.
- Consider nursing staff availability and patient care requirements.
- Keep resource transfers consistent with total resource availability.
- Distinguish transfers between departments from external changes in total resource availability.

The formal hard constraints are in Section 10.E.

### 3.6 Transparency and explainability

Every recommendation must come with an understandable explanation covering:

- The situation and problem detected.
- The relevant information used.
- The alternatives considered.
- The reasons for the selected allocation.
- The expected benefits and trade-offs.
- Any relevant uncertainty or limitation.

Decisions must be traceable and recorded.

### 3.7 Human oversight and ethical constraints

- The prototype assumes every agent decision is implemented automatically. This is a simplifying assumption of the simulated environment, not a claim of real-world authority.
- The agent is not authorized to make real-world clinical decisions.
- The agent must not discriminate against patients based on irrelevant personal characteristics.
- Clinical priority, fairness, resource conservation and operational feasibility remain fundamental constraints.

## 4. Data and Simulated Environment

The hospital datasets are generated **before** the agents begin their analysis, by a stochastic simulation that creates a synthetic hospital with evolving operational conditions.

**Principle: datasets contain only information that exists independently of the agents' decisions.** How beds and nurses are distributed across departments is an agent decision. It therefore lives only in the Allocation State, never in the input datasets.

The input data is specified field by field in [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md):

| Table | Grain | Content | Visible to agents |
| --- | --- | --- | --- |
| `hospital_resources_daily` | One row per day | Hospital-level pools of beds and nurses, and any external event | Yes, up to day t |
| `department_demand_daily` | One row per day and department | Arrivals, discharges and census by complexity level | Yes, up to day t |
| `patient_registry` | One row per patient | Patient ID, department, complexity, arrival day, discharge day | Only through tools, never `discharge_day` of present patients |
| `environment_config` | Static | Environment rules: the common bed cap `max_beds` and the nurse weights w(L1–L3) | Yes |
| `generation_config` | Static | True generation parameters: arrival rates, complexity mixes, length-of-stay distributions, surge, shocks, burn-in, seeds | **No, hidden from all agents** |

Rules:

- **Presence convention:** a patient is present on day d if `arrival_day ≤ d < discharge_day`. On the discharge day the bed is already free.
- **Horizon:** days in the horizon start at 1.
- **Warm start:** the generator simulates a **burn-in period** before day 1, so the hospital is already occupied on day 1. Burn-in patients have `arrival_day ≤ 0`.
- **End of horizon:** the generator simulates discharges beyond the horizon, so `discharge_day` is always the true value. All metrics are computed within the horizon only.
- **External shocks affect only the hospital-level pools** (total beds, total nurses), never a specific department.
- **Bed-cap feasibility:** `total_beds(t) ≤ 4 × max_beds` must hold for every t, including after positive shocks. This is a data-generation constraint, checked in data validation.
- **Hidden generation parameters:** agents never see the true generation parameters. Inferring demand patterns from history is part of the ALLOCATOR's adaptive role.
- **Deliberate redundancy:** `department_demand_daily` is derivable from `patient_registry`. Both are produced independently from the same simulation run, so that reconciling them is a genuine verification check rather than a tautology.
- The simulation is exclusively a data-generation mechanism and is not part of the agents' decision-making workflow.
- The agents operate on the generated datasets and do not continuously simulate new hospital events.

## 5. Multi-Agent Sequential Workflow

The system is built from four logical agents with separate responsibilities. [`docs/AGENTS.md`](docs/AGENTS.md) is the authoritative specification of their roles, implementation, tools and interactions.

| Agent | Role | Implementation |
| --- | --- | --- |
| **ANALYZER** | Interprets and records observed hospital conditions; makes no allocation decisions | Deterministic |
| **ALLOCATOR** | Makes one allocation decision per simulated day and records its reasoning | LLM subagent using tools |
| **CHECKER** | Independently audits recent decisions every five simulated days; never modifies decisions or blocks the workflow | Deterministic audit plus LLM subagent |
| **ORCHESTRATOR** | Enforces execution order, data access and record-keeping; makes no allocation decisions | Deterministic state machine |

The system operates sequentially, one day at a time. The complete dataset may exist from the beginning, but agents may only access information available up to the day being processed.

**Future observations must never influence earlier decisions.** This includes future-dated fields in the datasets: a discharge day later than the current day is future information.

Each simulated day follows the same cycle:

1. The ORCHESTRATOR starts the day and supplies the information available for it.
2. The ANALYZER compares the new observations with the previous recorded state and updates the observed hospital state.
3. The ALLOCATOR reassesses the current allocation and decides whether to maintain or modify it.
4. The decision is validated against the hard constraints, implemented and recorded with its reasoning.
5. Every fifth day, the CHECKER audits the decisions made since its previous audit.
6. The cycle repeats until the final day.

**Day 1:**

1. The common initial allocation, shared by the agent and all baselines (Section 10.L), is applied first.
2. Beds then go to the present patients according to the intra-department rule (Section 10.F).
3. The ALLOCATOR decides whether to maintain or modify the allocation, as on any other day.

**Deterministic environment rules.** Besides the four agents, the server contains a deterministic environment component. It applies pre-declared rules: the initial allocation, intra-department bed assignment, the hard-constraint validator and the failure repair rule. These rules are fixed before the run and involve no judgement. Allocations they produce are attributed to the rule, never to the ALLOCATOR.

Rules:

- Implemented decisions take effect immediately within the simulated environment.
- Previous decisions remain accessible as the decision history, and must be considered when making later decisions.
- Original input datasets are immutable. Observations, agent decisions, resulting allocation states and audit reports are recorded separately.
- State is kept in explicit, persistent records, never in conversational memory. A run must be resumable from any recorded day.
- The system must distinguish between:
  - Observed hospital conditions.
  - Resource allocations resulting from previous agent decisions.
  - New allocation decisions.
  - External changes in resource availability.

## 6. Results and Visualization

The project should eventually provide both static analytical outputs and dynamic visualizations.

**Static outputs** may include resource utilization indicators, average bed occupancy, nursing staff utilization, department-level comparisons, fairness indicators, allocation performance metrics and historical summaries of decisions.

**An interactive or animated visualization** should show resource movements between the four departments over time:

- Initial resource distributions.
- Transfers of beds and nurses between departments.
- Changes in resource allocations over time.
- The resulting allocation state on each day.

The visualization must reflect actual agent decisions and must not invent resource movements.

## 7. Evaluation and Reliability

Reliability is addressed at three distinct levels. They complement each other, and none substitutes for another.

| Level | Responsibility | When |
| --- | --- | --- |
| **Daily compliance** | The ALLOCATOR must respect every constraint in every decision; hard constraints are also validated when each decision is submitted | Every simulated day |
| **Periodic audit** | The CHECKER independently reviews recent decisions and documents errors, their causes and consequences | Every five simulated days |
| **Final evaluation** | The project measures overall system performance against baselines, using explicit metrics | After the simulation |

The CHECKER's five-day audit cycle is never permission to violate constraints on other days. Its reports are evidence for the final evaluation, not a replacement for it.

A central objective is to evaluate whether the agent actually improves resource allocation decisions. The final evaluation should investigate whether:

- Clinical priorities are respected.
- Resource allocations are fair.
- Available resources are used efficiently.
- Decisions remain operationally feasible.
- Sequential decisions lead to consistent outcomes.
- The agent makes avoidable or contradictory decisions.

The agent must be compared against simple baseline strategies under comparable simulated conditions (see Section 10.L).

Evaluation must rest on explicit metrics, reproducible experiments and independent verification. The project must critically examine the agent's limitations, potential errors and reliability.

**Independent verification.** The deterministic audit and the reconciliation of `department_demand_daily` against `patient_registry` are the project's independent evidence. Verification accounts for 20% of the grade. These checks must **not** depend on any LLM output.

**LLM non-determinism.** Only 1–3 agent runs are expected. The non-determinism of LLM decisions must be declared, and differences between runs are material for the Reflection.

**Do not assume an agent-generated recommendation is correct because it comes with a convincing explanation.**

## 8. Development Principles

- Prioritize correctness, transparency and reproducibility.
- Prefer simple, interpretable solutions over unnecessary complexity.
- Keep original data separate from derived data and agent-generated outputs.
- Preserve the traceability of all important decisions.
- Avoid unnecessary APIs, external services and infrastructure. The agents run as Claude Code subagents against a local Python MCP server: no API key, no paid APIs, no external services (see [`docs/AGENTS.md`](docs/AGENTS.md)).
- Enforce rules through code and permissions where possible, not only through instructions.
- Weigh the implementation cost and analytical value of any new feature before introducing it.
- Clearly distinguish established project decisions from assumptions and unresolved questions.

## 9. Working with Claude Code

Claude Code acts as a development assistant, analytical collaborator and critical reviewer.

- Treat [`docs/AGENTS.md`](docs/AGENTS.md) as the authoritative document for agent-specific roles, implementation, tools, inputs and outputs, execution order and state management. Read it before working on any agent.
- `CLAUDE.md` takes precedence on principles and constraints. If the two documents appear to conflict, raise the conflict with the project owner instead of resolving it silently.
- Keep the agents' responsibilities separate when implementing them. Do not let one agent take over another's role.
- Verify tool and configuration syntax (for example subagent frontmatter and MCP configuration) against current Claude Code documentation rather than guessing.
- Do not silently make conceptual decisions in the four escalation areas (Section 9.2). When one is required, explain the alternatives, give a recommendation and wait.
- **Reflection log:** whenever something goes wrong or nearly goes wrong (a wrong rationale, a false claim, a test or check that caught an error, a gap in enforcement), add an entry to [`docs/REFLECTION_LOG.md`](docs/REFLECTION_LOG.md) **at that moment**, not at the end of a session, and mention new entries in the session report. Errors by the AI assistant count.

### 9.1 Development sessions vs. run sessions

| | Development session | Run session |
| --- | --- | --- |
| Purpose | Writing code, documents and tests | Executing an agent run |
| Started as | A normal `claude` session | `claude --agent dispatcher --settings .claude/run-settings.json` |
| Tools | Normal development tools | Only the orchestration server and the `allocator` and `checker` subagents |
| Restrictions | None of the run restrictions apply | Deny rules on hidden data: deny-by-default on `data/**`, plus `docs/` and `src/data_generation/`, which contain the generation parameters. Start from the project root. Dispatch prompts are fixed templates that carry no data. The ALLOCATOR and CHECKER subagents run without `CLAUDE.md` (`omitClaudeMd`). Their prompts restate the principles they need and **must stay consistent with this file**. |
| Judgement | Normal collaboration | None: the dispatcher only calls workflow tools and invokes subagents in the required order |

Never run an agent run from a development session. Details are in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md).

### 9.2 Escalation rule

**Decide implementation-level choices yourself**, provided they do not affect any of these four areas:

1. Decision principles or hard constraints.
2. What information agents can see.
3. Metrics, baselines or evaluation design.
4. Data-generation parameters or distributions.

Rules:

- Tie-breaks, naming, file formats, atomic writes, caching and code layout are implementation-level.
- Record every implementation-level choice in the **Implementation Decisions Log** in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md): the date, the choice, the alternatives and a one-line rationale.
- **Escalate only items that touch the four areas.** Batch them, and include a recommendation for each.
- Never invent numerical parameters or operational assumptions in those areas. Leave them explicitly open until the project owner decides.

### 9.3 Design freeze

- The conceptual design is **frozen** as of 2026-11-07. Do not reopen settled decisions unless you find a genuine contradiction between them.
- Items still open are deferred until after the first data generation, unless they block current work.
- **Data freeze (2026-11-11):** the datasets are frozen at git tag `data-v1.0`; `data/MANIFEST.json` records their SHA-256 hashes and the generator commit. **Any change to data requires a new tag and the project owner's approval.** The manifest check must pass before any run.

## 10. Conceptual Decisions and Open Items

The following decisions are agreed at the conceptual level. They are project defaults for a synthetic environment, **not claims about real hospital operations**. The numerical parameter set and the escalation decisions of 2026-11-07 were approved by the owner. They are recorded in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) §10–11, and the current project status is in its §0.

Notation used below:

| Symbol | Meaning |
| --- | --- |
| B_d(t), N_d(t) | Beds and nurses allocated to department d on day t |
| P_B(t), P_N(t) | Hospital-level pools of beds and nurses on day t |
| O_d(t) | Beds in d still occupied on day t by patients who held a bed and have not been discharged |
| max_beds | Common maximum number of beds per department |

### 10.A Data generation

- Synthetic data is generated by a controlled stochastic simulation.
- Department-specific daily patient arrivals follow Poisson distributions with rate λ_d.
- Length of stay depends **only on clinical complexity level** and is the same across departments.
- Higher clinical complexity may be associated with longer stays and greater nursing requirements.
- Resource availability is constrained and may change through external shocks to the hospital-level pools.
- At least one department must include a **temporal trend or surge** (for example a mid-horizon surge), so that adaptive monitoring has something to detect.
- A **burn-in period** before day 1 produces a warm start, and discharges are simulated beyond the horizon (Section 4).
- `total_beds(t) ≤ 4 × max_beds` for every t is a generation constraint.
- Numerical parameters and distributions are **configurable**. The approved values are in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) §10. They are stored in `generation_config`, which is hidden from all agents.
- Do not claim that generated distributions represent real-world hospital statistics.

### 10.B Department profiles (P2)

- Departments differ **only** in complexity mix and Poisson arrival rate λ_d.
- There is no department multiplier for nursing intensity, and no department-specific length of stay.
- There is no ranking of departments by clinical priority. Clinical priority is determined by patient clinical complexity.

### 10.C Patient attributes

- The patient registry is deliberately minimal: unique patient ID, department, clinical complexity level, arrival day and discharge day.
- Do not introduce demographic, personal or sensitive attributes.
- Any additional attribute requires explicit justification and approval from the project owner.

### 10.D Resources and demand

**Beds**

- **Supply:** a hospital-level daily pool P_B(t), plus a maximum number of beds per department, `max_beds`, that is the **same for all departments**. The cap only prevents concentrating all beds in one department. Below the cap, department bed counts differ and are decided by the ALLOCATOR according to patient needs.
- **Demand:** one present patient requires one bed.
- **Overflow:** present patients beyond a department's allocated beds are *overflow*, measured as unmet demand by complexity level. Overflow is an outcome, not a constraint violation.

**Nurses**

- **Supply:** a single hospital-level pool P_N(t) of identical nurses, with no specialisation by level or department. It is an aggregate daily headcount, with no shifts.
- **Allocation:** the ALLOCATOR decides how many nurses go to each department every day. Nurses are **freely reassignable every day**; there is no no-eviction rule for nurses.
- **Demand (model N1):** `requirement_d(t) = ceil( Σ over present patients p in d of w(level_p) )`, with three weights w(L1), w(L2), w(L3). There is **no department multiplier**.
- The weights are treated as an **environment staffing norm** and are visible to agents.
- **Overflow patients require nurses.** This is consistent with N1, which counts all present patients.
- **Intra-department nurse coverage:** within a department, nurses cover patients in descending complexity (L3 first). Any shortage is therefore attributed to levels from the lowest upward.
- **Shortage:** nurses allocated below the requirement, measured as an outcome.

### 10.E Hard constraints and measured outcomes

Violating any hard constraint is an ALLOCATOR error.

1. **Conservation:** `Σ_d B_d(t) = P_B(t)` and `Σ_d N_d(t) = P_N(t)`.
2. **Bounds and integrality:** `0 ≤ B_d(t) ≤ max_beds`, `N_d(t) ≥ 0`, all integers.
3. **No-eviction:** `B_d(t) ≥ O_d(t)`. Occupied beds are never taken away, in particular never to give the bed to a higher-level patient. Occupied beds are removed **only** because of exogenous shocks.
4. **Relaxed no-eviction under shocks:** if `Σ_d O_d(t) > P_B(t)`, the ALLOCATOR must cut exactly the shortfall and not one bed more: `Σ_d max(0, O_d(t) − B_d(t)) = Σ_d O_d(t) − P_B(t)`. It chooses which department(s) absorb the cut. The evicted patients become overflow.

**Measured outcomes (not violations):**

- Bed overflow by level.
- Nurse shortage relative to the N1 requirement, by level.
- Idle beds and nurses.
- Number and size of reallocations (stability cost).

### 10.F Intra-department bed assignment rule

The ALLOCATOR assigns beds to **departments, not to patients**. Which patients hold a bed is determined by a deterministic rule:

1. A patient who holds a bed keeps it until discharge.
2. Free beds in a department go to its overflow patients in **descending complexity**. Ties within a level are broken by **arrival order**: longest-waiting first, measured from `arrival_day`.
3. Only under a shock-driven cut, if occupied beds in a department are removed, the **lowest-level** patients lose them first.

A deterministic **environment component** in the server runs this rule whenever an allocation takes effect: the initial allocation, an accepted decision or a repair. It writes the **Bed Assignment State**, recording per patient and per day whether the patient is in a bed or in overflow, and in which department. It is the only writer of that record.

On day 1, the rule assigns the initial allocation's beds to the patients present after burn-in. **No-eviction then protects those patients** during the ALLOCATOR's day-1 decision (confirmed).

Residual tie-breaks (for example equal `arrival_day`) are implementation-level and are recorded in the Implementation Decisions Log.

### 10.G Clinical priority violations and severity

- **Beds:** on day t a patient of level k is in overflow in department d, while the ALLOCATOR either:
  - assigned a *movable* bed (free, or freed by that day's discharges) to a department d′ where it serves a patient of level < k, or
  - left that bed empty,

  and the cap of d would have allowed assigning the bed to d.
- **Beds under shock:** it is also a violation to cut the bed of a level-k patient when the bed of a patient of level < k in another department could have been cut instead.
- **Nurses:** a violation also occurs when higher-level patients in d are uncovered while lower-level patients are covered elsewhere. Coverage follows the intra-department rule in Section 10.D. There is no movability condition, because nurses are freely reassignable.
- **Severity of a clinical violation** = the level difference between the unserved patient and the patient served in their place.
- The general severity scale for other issue types was fixed on 2026-11-12 ([`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) §4).

### 10.H Fairness

- **Comparable clinical needs** means the **same complexity level**.
- **F1, the ALLOCATOR's guiding criterion:** among patients of the same level, the longest-waiting patient has precedence, regardless of department. F1 guides the ALLOCATOR's judgement; it is not a hard-coded rule.
- **Waiting is measured from `arrival_day`**, both for F1 and for the intra-department tie-break. Patients evicted by a shock therefore regain priority quickly. This is intended, because they lost their bed for an exogenous reason.
- **F2, evaluation metrics, computed per level:**
  - Dispersion across departments of the overflow rate (max − min).
  - Mean days in overflow.
  - Relative nurse coverage.
- The fairness–efficiency trade-off shows up as reallocation frequency and size. By Section 3.2, fairness prevails at a moderate efficiency cost.

### 10.I Decision process

- The ALLOCATOR makes one allocation decision per simulated day, after the ANALYZER has processed that day's observations. The decision may maintain or modify the existing allocation.
- The ALLOCATOR is an LLM agent that operates through **explicit tool calls**, as the course instructor requires. It can test alternatives with a what-if tool before submitting.
- The process evaluates feasible alternatives subject to clinical priority, fairness, efficiency and operational feasibility, in the hierarchy defined in Section 3.
- Prefer a transparent, constrained decision process over an opaque objective function with arbitrary weights.
- Do not introduce a sophisticated optimization solver unless the project requirements and available time justify it.
- Failure handling for rejected decisions is specified in [`docs/AGENTS.md`](docs/AGENTS.md).

### 10.J Internal memory

- The system uses explicit, persistent state and decision records.
- Do not rely on a model's conversational memory to preserve hospital conditions or previous decisions.
- All relevant information must be recoverable from structured project records, so that a run can be resumed from any day.

### 10.K Visualization

The project produces two complementary types of output:

1. **Static analytical visualizations:** resource utilization, department-level allocation patterns, clinical priority and fairness indicators, and evaluation metrics.
2. **A dynamic or animated visualization:** the evolution of resource allocation over time, movements of beds and nurses between departments, and changes in allocation across simulated days.

Keep the visualization approach simple enough to implement within the project deadline.

### 10.L Evaluation and baselines

The evaluation covers:

- Clinical priority compliance.
- Fairness.
- Efficiency.
- Operational feasibility.
- Resource conservation.
- Sequential consistency and stability.

**Candidate metrics** (not necessarily final):

- Number and severity of clinical priority violations (Section 10.G).
- Bed overflow and nurse shortage by clinical level.
- Fairness metrics F2 (Section 10.H).
- Resource utilization.
- Idle beds and nurses.
- Number and magnitude of reallocations.
- Hard-constraint violations (Section 10.E).

Define precise formulas only after the allocation rules and data structure are established.

**Baselines** (simple and reproducible):

- **No reallocation:** maintain the initial allocation.
- **Clinical-priority-first:** a simple deterministic rule.
- **Proportional or demand-based:** a simple proportional allocation.

**Initial allocation:** common to the agent and all baselines. It is proportional to the day-1 census, within the bed cap.

**Same environment:** the baselines start from the same initial allocation and run through the same environment as the agent:

- The same datasets.
- The same hard constraints, including no-eviction.
- The same intra-department bed assignment rule.
- The same deterministic audit.

**Feasibility projection:** every baseline computes its target allocation and then projects it onto the feasible set, respecting all hard constraints including no-eviction.

| Baseline | Beds | Nurses |
| --- | --- | --- |
| **No reallocation** | Previous allocation, adapted each day by the repair rule | Previous allocation, adapted each day by the repair rule |
| **Clinical-priority-first** | Occupied beds are kept. Each movable bed goes to the highest-level overflow patient hospital-wide (ties by `arrival_day`, then `patient_id`), within the cap. Leftover beds are split in proportion to census. Shock cuts follow the repair rule. | Cover the L3 requirement hospital-wide first, then L2, then L1. Leftover nurses are split in proportion to the N1 requirement. |
| **Proportional** | Target proportional to census (largest remainder). Floors `B_d ≥ O_d`, the remainder spread in proportion to the unmet target, then the cap applied. | In proportion to the N1 requirement |

Algorithms are specified in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md).

**Within-day timing (confirmed):** discharges → arrivals → observation → allocation → bed assignment.

Rules:

- The AI agent is evaluated against these baselines under comparable simulated conditions.
- Do not claim that a baseline is optimal unless optimality has actually been established.
- The CHECKER's reports provide additional qualitative and quantitative evidence about the agent's errors.
- The ALLOCATOR does not read validation reports in the main run. A feedback run, in which it does, may be added later as an ablation.

### 10.M Still open

The following remain undecided. They are deferred until after the first data generation, unless they block current work. Do not settle them without the project owner's agreement (Section 9.2).

- **Headline metric set:** the formulas and the CHECKER severity scale were fixed on 2026-11-12, before any agent output ([`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) §3–§4). The headline set is confirmed after the owner reviews the baseline headroom (§8 there).
- **Visualization:** tools and design.
