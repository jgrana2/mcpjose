This repo includes Agent Skills (https://agentskills.io) under `.agents/skills/`.

How to use depends on your agent host:

- Codex: skills are auto-discovered from `.agents/skills/`.
- Claude Code / others: either configure this path as a skills directory, or symlink/copy the skill folders into the location your tool watches.

Included skills:

- `.agents/skills/mcpjose-research/`: workflow for web/PDF/X research using this repo's `mcpjose` MCP server tools.
