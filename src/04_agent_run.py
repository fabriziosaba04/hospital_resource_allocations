"""Step 4: the agent runs R1, R2, R3 (seed20261107) and STRESS1 (seed20261107_stress). NOT re-runnable by a grader.

    uv run python src/04_agent_run.py          # prints the commands; executes nothing

A run needs the `claude` CLI with a subscription, a clone outside any synced folder (Log #90) checked out at the
tag prompts-v1.0, and a fresh shell; LLM decisions are non-deterministic, so a new run is a new run, never a
reproduction. The four committed runs are the evidence; steps 5-9 verify and analyse them without the agent.
Run-session restrictions: .claude/run-settings.json; dispatcher, ALLOCATOR and CHECKER: .claude/agents/.
"""

COMMANDS = """\
# in a clone outside OneDrive, at prompts-v1.0 (owner machine; see PROJECT_SPEC.md sections 0 and 8)
git clone <repo> C:/hra-runs/hospital_resource_allocations && cd C:/hra-runs/hospital_resource_allocations
git checkout prompts-v1.0 && uv sync
uv run python -m src.mcp_server.init_run --dataset seed20261107 --run-id R1    # manifest check, run folder, ACTIVE_RUN
uv run python -m src.mcp_server.launch                                          # exits 1 unless FINISHED; re-run to resume
# back in the repository: copy the run folders and the subagent capture, hash-checked
uv run python -m src.mcp_server.copy_back C:/hra-runs/hospital_resource_allocations R1
# R2, R3: same dataset; STRESS1: --dataset seed20261107_stress
"""

if __name__ == "__main__":
    print(COMMANDS)
