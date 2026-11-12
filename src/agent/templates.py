"""Fixed dispatch templates (PROJECT_SPEC.md §8). Constant strings that carry no data.

The dispatcher has no file tools, so the same strings are written verbatim into
.claude/agents/dispatcher.md; tests/test_mcp_server.py checks that they match.
"""

ALLOCATE = "Make today's allocation decision using your tools."
AUDIT = "Audit the decisions of the current five-day period using your tools, then submit your validation report."
