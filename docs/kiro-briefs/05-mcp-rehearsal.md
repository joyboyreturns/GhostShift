# Session 5: Kiro rehearses a playbook through the GhostShift MCP server

Prerequisite: the API is running (`make dev`) and Kiro loads `.kiro/settings/mcp.json` (server
`ghostshift`, defined in scripts/ghostshift_mcp.py). First list the tools to confirm they load; if the server
does not load, fix the configuration and say what was wrong.

1. Use the MCP tools (not shell or curl) to list demos, start a rehearsal of `night-market` allowing draft
   rehearsal, make choices, reach the ghost path, verify replay, and fetch the report.
2. Edit `fixtures/night-market/runbook.md` in a scratch copy under `/tmp` (never the original) to add a sentence
   covering the indoor-full case, and explain what a re-run would need. Do not modify tracked fixtures.
3. Write `.kiro/steering/ghost-path-testing.md`: durable steering for how contributors should rehearse
   and scan playbooks before changing them, based on what you actually observed.
4. Quote the real tool calls and results in your final message so they can be copied into
   docs/kiro-evidence.md. Record failures too.
