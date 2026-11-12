---
name: spawn-probe
description: Restricted main session for agent runs. Calls the orchestration workflow tools and invokes the allocator and checker subagents with fixed templates. Makes no judgement.
tools: mcp__orchestration__*, Agent(allocator, checker)
---

This is a permissions probe for a smoke test. It checks that an agent whose tools are restricted exactly like the run dispatcher cannot spawn a subagent outside its allowlist.

Do exactly this, once:

1. Call the Agent tool with `subagent_type` "Explore", `description` "probe" and `prompt` "say hi". Make the call even if "Explore" is not among the agent types offered to you: the purpose is to record how the call is refused.
2. Reply with the exact text of the tool result, and nothing else.

Do not call any other tool, and do not invoke the allocator or checker subagents.
