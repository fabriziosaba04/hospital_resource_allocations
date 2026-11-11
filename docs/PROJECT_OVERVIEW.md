# Project Overview

## The problem

Hospitals must distribute limited beds and nursing staff across departments whose demand changes from day to day. A fixed distribution soon becomes unbalanced. One department overflows while another has idle beds, and staff shortages fall unevenly on patients.

Reallocating resources well means weighing three things at once:

- **Clinical need:** the sickest patients come first.
- **Fairness:** patients with the same need should have the same access, whatever their department.
- **Efficiency:** idle resources should be avoided.

All of this must happen without disrupting patients already in care.

## What the project builds

An AI decision-support system, the **Hospital Resource Allocation Agent**, that reallocates beds and nurses across four departments of a **simulated** hospital, one day at a time:

- **Departments:** Internal Medicine, Cardiology, Neurology and Orthopedics.
- **Patients:** each has one of three complexity levels, with Level 3 the highest priority.
- **Explanation:** every decision is explained and recorded.
- **Audit:** an independent audit checks the decisions.

The system is a research prototype. It is not intended to manage a real hospital or to replace human decision-makers.

## Data

The data is synthetic, generated before any agent runs by a stochastic simulation. It includes:

- Poisson arrivals.
- Length of stay that depends on complexity.
- A demand surge in one department.
- External shocks to the hospital's total beds and nurses.

The data contains only facts that exist independently of the agent. How resources are split across departments is the agent's decision and is never in the data.

## Architecture at a glance

| Agent | What it does | How |
| --- | --- | --- |
| **ANALYZER** | Reads each day's observations and records the hospital's situation | Deterministic code |
| **ALLOCATOR** | Decides how many beds and nurses each department gets, and explains why | LLM agent using tools |
| **CHECKER** | Every five days, audits the recent decisions | Deterministic audit plus LLM review |
| **ORCHESTRATOR** | Enforces the daily sequence and data access | Deterministic state machine |

Everything runs locally:

- The agents are Claude Code subagents that act only through the tools of a local Python MCP server.
- Each role gets its own tools, so rules are enforced by permissions as well as instructions.
- Agents never see future data or the parameters used to generate the data.

**Key rules:**

- Clinical priority is never sacrificed.
- Occupied beds are never taken away, except for an external shock.
- Resources are never created.
- Every decision includes its reasoning and the alternatives considered.

## Evaluation approach

The agent is compared with three deterministic baselines on the same data and rules:

- No reallocation.
- Clinical-priority-first.
- Proportional allocation.

The metrics cover:

- Clinical priority violations and their severity.
- Fairness across departments within each complexity level.
- Overflow and nurse shortage by level.
- Idle resources.
- Stability of decisions over time.

Two checks are independent of any AI output: a deterministic audit, and the reconciliation of two independently produced datasets. They are the project's main evidence. The agent runs one to three times, and the differences between runs are reported as part of the reflection on its reliability.

## Scope limits

- One simulated hospital, four departments, two resources (beds and nurses), three complexity levels.
- No shifts, no staff specialisation, and no patient attributes beyond department, complexity and dates.
- Decisions are implemented automatically in the simulation. That is a simplification, not a claim of real-world authority.
- The generated distributions are illustrative, not real hospital statistics.

## Where to read more

| Document | Content |
| --- | --- |
| [`CLAUDE.md`](../CLAUDE.md) | Principles, constraints and decisions |
| [`AGENTS.md`](AGENTS.md) | Agent roles and workflow |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | Technical design |
| [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) | Data fields |
| [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) | Metrics and run plan |
