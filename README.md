# Hospital Resource Allocation Agent

An AI decision-support prototype that reallocates beds and nurses across four departments of a simulated hospital, one day at a time. It balances clinical priority, fairness and efficiency.

- **Agents:** an LLM ALLOCATOR acts through the tools of a local MCP server, while deterministic components analyse the hospital, enforce the workflow and audit the decisions.
- **Evaluation:** the agent is compared with deterministic baselines on synthetic data.

This is a Business Analytics course project. Start with [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md).

> **Status:** data generated and frozen (tag `data-v1.0`, verified by `uv run python -m src.data_generation.manifest --verify`). Agents, MCP server and evaluation are not built yet; their commands below are planned.

## Repository structure

```text
.
├── CLAUDE.md                 principles, constraints, decisions (main reference)
├── .mcp.json                 orchestration MCP server (planned)
├── .claude/
│   ├── run-settings.json     run-session restrictions (planned)
│   └── agents/               dispatcher, allocator, checker definitions (planned)
├── docs/                     overview, spec, agents, data dictionary, evaluation, reflection
├── data/
│   ├── raw/                  generated input tables, per dataset (immutable)
│   ├── processed/            dataset validation reports
│   └── metadata/             environment and generation configs
├── src/
│   ├── data_generation/      synthetic data generator and checks
│   ├── environment/          deterministic rules shared by server and baselines
│   ├── mcp_server/           MCP server (orchestration / allocator / checker roles)
│   ├── agent/                subagent prompts and dispatch templates
│   ├── evaluation/           deterministic audit, metrics, baselines
│   └── utils/
├── results/
│   ├── allocations/          run records (state, decisions, allocations)
│   ├── evaluations/          audits, validation reports, metrics
│   └── visualizations/
├── tests/
└── notebooks/
```

## Setup

Requirements: [uv](https://docs.astral.sh/uv/) and [Claude Code](https://code.claude.com/). No API key or paid service is needed.

```bash
# install uv (see the uv documentation for other methods)
# Windows (PowerShell):  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:           curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync          # create the virtual environment and install dependencies (once pyproject.toml exists)
uv run pytest    # run the tests
```

## Usage (placeholders)

```bash
# 1. Generate and validate a dataset
uv run python -m src.data_generation --config <generation_config> --env <environment_config> --seed <seed>

# 2. Run the deterministic baselines
uv run python -m src.evaluation.baselines --dataset <dataset_id>

# 3. Initialise an agent run (in a development session or terminal)
uv run python -m src.mcp_server.init_run --dataset <dataset_id>

# 4. Execute the agent run in a restricted run session
claude --agent dispatcher --settings .claude/run-settings.json

# 5. Compute metrics and figures
uv run python -m src.evaluation.metrics --run <run_id>
```

Run sessions and development sessions are different. See `CLAUDE.md` §9.1.

## Documentation

| Document | Content |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) | Principles, constraints and decisions |
| [`docs/AGENTS.md`](docs/AGENTS.md) | Agent roles and workflow |
| [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) | Technical design and the Implementation Decisions Log |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Data fields |
| [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) | Metrics, baselines and run plan |
| [`docs/LIMITATIONS_AND_REFLECTION.md`](docs/LIMITATIONS_AND_REFLECTION.md) | Limitations and reflection (to be written) |
