---
name: agent-team
description: Use for spawning and managing agent teams with mcpjose_spawn_agent, mcpjose_spawn_agent_team, and related tools. Best for delegating complex tasks to sub-agents.
---

# agent-team

This skill provides instructions for using the agent team features in MCP Jose to delegate tasks to sub-agents.

## Tools

- `mcpjose_spawn_agent` - Spawn a single agent to execute a task
- `mcpjose_spawn_agent_team` - Spawn a complete team from a DECOMPOSITION.md plan
- `mcpjose_get_team_status` - Check team/task progress
- `mcpjose_send_message_to_agent` - Send messages between agents
- `mcpjose_wait_for_team` - Wait for all tasks to complete
- `mcpjose_shutdown_team` - Shutdown all agents in a team

## Spawning Single Agents

Use `mcpjose_spawn_agent` for one-off tasks that don't require a pre-existing plan.

### Parameters

| Parameter | Required | Notes |
|-----------|----------|-------|
| `team_id` | Yes | Unique identifier for the team (e.g., "research", "project-alpha") |
| `agent_type` | Yes | "opencode", "claude_code", or "langchain_subagent" |
| `role` | Yes | Agent's function (e.g., "researcher", "developer", "qa_engineer") |
| `action` | Yes* | Task description (*unless `task_id` provided) |
| `task_id` | No | Existing task ID from task board (rarely needed) |
| `work_dir` | No | Custom work directory (default: workflows/{team_id}) |
| `plan_mode` | No | Spawn in plan mode for safety (default: true) |
| `timeout_minutes` | No | Max runtime (default: 30) |

### Examples

**Basic usage:**
```python
from tools.agent_spawner import spawn_agent

result = spawn_agent(
    team_id="research-team",
    agent_type="opencode",
    role="researcher",
    action="Research latest AI news and trends",
    timeout_minutes=5
)
```

**Multiple agents in same team:**
```python
spawn_agent(
    team_id="project-alpha",
    agent_type="opencode",
    role="developer",
    action="Implement user authentication"
)
spawn_agent(
    team_id="project-alpha",
    agent_type="opencode",
    role="qa_engineer",
    action="Write tests for auth module"
)
```

## Spawning Agent Teams

Use `mcpjose_spawn_agent_team` for complex workflows with multiple tasks from a plan.

### Requirements

1. A plan directory containing:
   - `AtomicTasks.json` - Task definitions
   - `TaskTree.json` - Task hierarchy

2. Tasks in `AtomicTasks.json` should have clear roles assigned via `tool_or_endpoint` or action keywords

### Example

```python
from tools.agent_spawner import spawn_agent_team

result = spawn_agent_team(
    team_id="my-project",
    plan_dir="userapp/Plan",
    max_parallel=3  # Max agents to spawn at once
)
```

## Monitoring Progress

### Check team status:
```python
from tools.agent_spawner import get_team_status

status = get_team_status(team_id="research-team")
# Returns: {tasks: {total, completed, failed, in_progress, pending}, agents: {...}}
```

### Check individual task:
```python
# Read the team's task_board.json
read_file(path="workflows/{team_id}/task_board.json")

# Read agent status
read_file(path="workflows/{team_id}/artifacts/{agent_id}/status.json")
```

### Check agent output:
```python
read_file(path="workflows/{team_id}/artifacts/{agent_id}/output.log")
```

## Inter-Agent Communication

### Send message to agent:
```python
from tools.agent_spawner import send_message_to_agent

send_message_to_agent(
    team_id="project-alpha",
    from_agent="coordinator",
    to_agent="opencode_developer_123",
    message_type="status_update",
    content="Please prioritize the auth module"
)
```

### Wait for team completion:
```python
from tools.agent_spawner import wait_for_team

result = wait_for_team(
    team_id="project-alpha",
    timeout=600  # seconds
)
```

## Workflows

### Research Workflow
1. Spawn researcher agent with `action="Research {topic}"`
2. Poll `get_team_status` or check `status.json`
3. Read report from `artifacts/{agent_id}/{report_file}.md`

### Code Review Workflow
1. Spawn reviewer agent with specific action
2. Agent reads code, runs tests, writes review report
3. Read findings from agent artifacts

### Multi-Task Workflow
1. Use `spawn_agent_team` with plan directory
2. Set `max_parallel` to control concurrency
3. Use `wait_for_team` to wait for completion
4. Aggregate results from all agent artifacts

## Output Locations

All agent outputs are stored in:
```
workflows/{team_id}/
├── artifacts/{agent_id}/
│   ├── agent_manifest.json    # Agent metadata
│   ├── status.json            # Completion status
│   ├── output.log             # Execution log
│   └── *.md                   # Deliverables (reports, etc.)
├── task_board.json           # Task status tracker
├── messages.json             # Inter-agent messages
└── team_config.json          # Team configuration
```

## Best Practices

1. **Always provide `action`** - Don't rely on `task_id` unless you have an existing task
2. **Use clear, specific actions** - "Research AI news April 2026" not just "research"
3. **Set appropriate timeout** - Short for simple tasks (5 min), longer for complex ones (30+ min)
4. **Check status after timeout** - Some status updates may be delayed
5. **Use meaningful team_ids** - Makes it easier to track multiple teams
6. **Use roles strategically** - Helps track what each agent is doing (researcher, developer, etc.)

## Common Issues

- **"Task not found"**: Provide `action` to create task on-the-fly, or ensure `task_id` exists
- **Status not updating**: Check `artifacts/{agent_id}/status.json` directly
- **Agent not completing**: Check `artifacts/{agent_id}/output.log` for errors

## Tools Reference

See `references/mcpjose-tools.md` for the full list of MCP Jose tools.
