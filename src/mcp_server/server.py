"""MCP tool layer: one server instance per role, each registering only its own tools (AGENTS.md §2.1).

Every tool builds a fresh `Workflow` from the active-run pointer, so nothing is cached between calls.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .store import StoreError
from .workflow import Workflow as _Workflow
from .workflow import WorkflowError


class Workflow:
    """Proxy that turns workflow and store errors into ToolError, so the agent sees the message
    (including the expected next action) instead of the SDK's generic crash text."""

    def __init__(self):
        try:
            self._wf = _Workflow()
        except (StoreError, WorkflowError) as e:
            raise ToolError(str(e)) from e

    def __getattr__(self, name):
        fn = getattr(self._wf, name)

        def call(*a, **k):
            try:
                return fn(*a, **k)
            except (StoreError, WorkflowError) as e:
                raise ToolError(str(e)) from e
        return call

ROLE_TOOLS = {
    "orchestration": ("get_workflow_status", "advance_day", "end_allocation_phase", "close_day"),
    "allocator": ("get_observed_state", "get_allocation_state", "get_decision_history", "get_overflow_queue",
                  "simulate_allocation", "validate_allocation", "submit_decision"),
    "checker": ("get_deterministic_audit", "get_decision_history", "get_observed_state", "submit_validation_report"),
}


def build(role: str) -> MCPServer:
    if role not in ROLE_TOOLS:
        raise ValueError(f"unknown role {role!r}")
    srv = MCPServer(role)

    if role == "orchestration":
        @srv.tool()
        def get_workflow_status() -> dict:
            """Run ID, current day, phase and the expected next action. Returns no hospital data."""
            return Workflow().get_workflow_status()

        @srv.tool()
        def advance_day() -> dict:
            """Move to the next day: on day 1 apply the initial allocation, then run the ANALYZER."""
            return Workflow().advance_day()

        @srv.tool()
        def end_allocation_phase() -> dict:
            """End today's allocation phase: repair if no decision was accepted, assign beds, audit on day t mod 5 = 0."""
            return Workflow().end_allocation_phase()

        @srv.tool()
        def close_day() -> dict:
            """Close the day (records an LLM CHECKER failure if an audit had no report)."""
            return Workflow().close_day()

    elif role == "allocator":
        @srv.tool()
        def get_observed_state() -> dict:
            """Today's Observed State from the ANALYZER: pools, external changes, per-department demand,
            occupied beds and N1 nurse requirement."""
            return Workflow().get_observed_state()

        @srv.tool()
        def get_allocation_state() -> dict:
            """The allocation in effect (beds and nurses per department), its source, and the allocation history."""
            return Workflow().get_allocation_state()

        @srv.tool()
        def get_decision_history() -> dict:
            """All your previous decisions, explanations and submission attempts."""
            return Workflow().get_decision_history()

        @srv.tool()
        def get_overflow_queue() -> dict:
            """Patients present today who do not hold a bed from yesterday, with level, arrival day and days waiting."""
            return Workflow().get_overflow_queue()

        @srv.tool()
        def simulate_allocation(beds: dict[str, Any], nurses: dict[str, Any]) -> dict:
            """What-if for today only, no writes: validator result, overflow and nurse coverage by department and
            level, and clinical-priority violations of the proposal."""
            return Workflow().simulate_allocation(beds, nurses)

        @srv.tool()
        def validate_allocation(beds: dict[str, Any], nurses: dict[str, Any]) -> dict:
            """Hard-constraint check only. Free: does not count as a submission attempt."""
            return Workflow().validate_allocation(beds, nurses)

        @srv.tool()
        def submit_decision(beds: dict[str, Any], nurses: dict[str, Any], explanation: dict[str, Any]) -> dict:
            """Submit today's decision. explanation needs the fields situation, information_used, alternatives,
            reasons, tradeoffs, uncertainty. At most one accepted decision per day, at most 3 attempts."""
            return Workflow().submit_decision(beds, nurses, explanation)

    else:
        @srv.tool()
        def get_deterministic_audit(from_day: int | None = None, to_day: int | None = None) -> dict:
            """The stored Deterministic Audit Record for the period (default: the current five-day period)."""
            return Workflow().get_deterministic_audit(from_day, to_day)

        @srv.tool()
        def get_decision_history(from_day: int | None = None, to_day: int | None = None) -> dict:
            """The ALLOCATOR's decisions, explanations, attempts and allocations for the period."""
            return Workflow().checker_decision_history(from_day, to_day)

        @srv.tool()
        def get_observed_state(from_day: int | None = None, to_day: int | None = None) -> dict:
            """The Observed States for the period."""
            return Workflow().checker_observed_state(from_day, to_day)

        @srv.tool()
        def submit_validation_report(report: dict[str, Any]) -> dict:
            """Submit the audit report: {period, checked, issues, summary}. Accepted once per audit."""
            return Workflow().submit_validation_report(report)

    return srv
