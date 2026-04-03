# Agentic OS - Agent Team Orchestration

The Agentic OS is a multi-agent orchestration system that enables cross-functional agent teams to work together on complex tasks. It unifies OpenCode, Claude Code, and LangChain agents under a single coordination framework.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agentic OS Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LangChain Agent (Orchestrator)              │   │
│  │  - Uses DECOMPOSITION.md for planning                   │   │
│  │  - Spawns and manages agent teams                       │   │
│  │  - Synthesizes results                                  │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Agent Team Coordinator                      │   │
│  │  - Manages shared task board (JSON)                     │   │
│  │  - Handles inter-agent messaging (JSON)                 │   │
│  │  - Tracks agent lifecycle                               │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│          ┌────────────┼────────────┐                            │
│          │            │            │                            │
│          ▼            ▼            ▼                            │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐                       │
│    │OpenCode │  │ Claude  │  │LangChain│                       │
│    │ Session │  │ Code    │  │Subagent │                       │
│    │(spawned)│  │ Session │  │(in-proc)│                       │
│    └─────────┘  └─────────┘  └─────────┘                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Shared JSON State                          │   │
│  │         (workflows/{team_id}/*.json)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Create and Run a Team from a User Request

```python
from langchain_agent.agent import MCPJoseLangChainAgent

# Create the orchestrator
orchestrator = MCPJoseLangChainAgent()

# Orchestrate a team
result = orchestrator.orchestrate_team(
    user_request="Build a Python REST API with FastAPI",
    team_id="my_api_project",
    max_parallel=5,
)

print(f"Team {result['team_id']} completed!")
```

### 2. Use an Existing Plan Directory

```python
result = orchestrator.orchestrate_team(
    user_request="Build a Python REST API",
    team_id="my_api_project",
    use_plan_dir="userapp/Plan",  # Use existing DECOMPOSITION.md plan
    max_parallel=5,
)
```

### 3. CLI Usage

```bash
# Create a team from a user request
python cli.py team create --request "Build a Python REST API" --team-id my_api --wait

# Spawn agents from existing plan
python cli.py team spawn --team-id my_api --plan-dir userapp/Plan --max-parallel 5

# Check team status
python cli.py team status my_api

# Send message to team
python cli.py team message --team-id my_api --to-agent broadcast --content "Status update?"

# Wait for completion
python cli.py team wait my_api --timeout 3600

# Shutdown team
python cli.py team shutdown my_api

# List all teams
python cli.py team list
```

## Agent Roles

The system automatically assigns roles based on task content:

| Role | Description | Best For |
|------|-------------|----------|
| `business_analyst` | Requirements analysis, stakeholder communication | Requirements gathering, documentation |
| `tech_lead` | Architecture, implementation oversight | Code reviews, system design |
| `developer` | Implementation, coding | Writing code, refactoring |
| `qa_engineer` | Testing, validation | Test writing, bug verification |
| `devops_engineer` | Deployment, infrastructure | CI/CD, infrastructure as code |
| `researcher` | Investigation, data analysis | Research tasks, data gathering |
| `ux_designer` | User experience, interface design | UI/UX work, design systems |
| `generalist` | General purpose | Simple tasks, quick queries |

## Agent Types

### OpenCode
- **Best for**: Complex coding tasks, multi-file changes
- **Spawns**: External OpenCode CLI process
- **Communication**: JSON files
- **Safety**: Plan mode available

### Claude Code
- **Best for**: Complex development, code review
- **Spawns**: External Claude Code CLI process
- **Communication**: JSON files
- **Safety**: Plan mode available

### LangChain Subagent
- **Best for**: Quick research, simple tool calls
- **Runs**: In-process (same Python process)
- **Communication**: Direct method calls + JSON
- **Safety**: Limited by tool registry permissions

## Shared State Structure

Teams communicate via JSON files in `workflows/{team_id}/`:

```
workflows/{team_id}/
├── team_config.json          # Team metadata
├── task_board.json           # Shared task list
│   {
│     "tasks": [
│       {
│         "task_id": "1.1.1",
│         "status": "in_progress",
│         "assigned_to": "oc_developer_12345",
│         "dependencies": ["1.1"],
│         ...
│       }
│     ]
│   }
├── messages.json             # Inter-agent message bus
│   {
│     "messages": [
│       {
│         "id": "msg_001",
│         "from": "coordinator",
│         "to": "oc_developer_12345",
│         "type": "instruction",
│         "content": {...},
│         "timestamp": "..."
│       }
│     ]
│   }
├── artifacts/
│   ├── oc_developer_12345/   # Each agent's output
│   │   ├── agent_manifest.json
│   │   ├── status.json
│   │   ├── output.log
│   │   └── ...
│   └── ...
└── checkpoint.json           # For resuming
```

## Task Dependencies

Tasks can have dependencies that must be completed before they can start:

```json
{
  "task_id": "1.1.2",
  "dependencies": ["1.1.1"],
  "status": "blocked"
}
```

The coordinator automatically:
- Tracks dependency completion
- Blocks tasks until dependencies are met
- Unblocks tasks when dependencies complete

## API Reference

### AgentTeamCoordinator

```python
from core.agent_team import AgentTeamCoordinator

coordinator = AgentTeamCoordinator("team_id", Path("workflows/team_id"))

# Initialize from plan
coordinator.initialize_from_plan(Path("userapp/Plan"))

# Or create dynamic plan
coordinator.create_dynamic_plan(user_request, atomic_tasks)

# Spawn agents
agent = coordinator.spawn_agent(AgentType.OPENCODE, "developer", "1.1.1")

# Check status
progress = coordinator.get_progress()

# Wait for completion
result = coordinator.wait_for_completion(timeout=3600)

# Get results
results = coordinator.get_results()

# Shutdown
.coordinator.shutdown_all()
```

### Tools (via ProjectToolRegistry)

```python
# Spawn single agent
tool_registry.spawn_agent(
    team_id="my_team",
    agent_type="opencode",
    role="developer",
    task_id="1.1.1",
)

# Spawn full team from plan
tool_registry.spawn_agent_team(
    team_id="my_team",
    plan_dir="userapp/Plan",
    max_parallel=5,
)

# Get status
tool_registry.get_team_status(team_id="my_team")

# Send message
tool_registry.send_message_to_agent(
    team_id="my_team",
    from_agent="user",
    to_agent="broadcast",
    message_type="instruction",
    content="Priority changed: focus on auth first",
)

# Wait for completion
tool_registry.wait_for_team(team_id="my_team")

# Shutdown
tool_registry.shutdown_team(team_id="my_team")
```

## Integration with DECOMPOSITION.md

The Agentic OS integrates seamlessly with the existing DECOMPOSITION.md framework:

1. **Plan Generation**: The orchestrator can generate plans using DECOMPOSITION.md as a skill
2. **Plan Loading**: Can load existing plans from `userapp/Plan/`
3. **Task Execution**: Atomic tasks are assigned to appropriate agent types based on content
4. **Validation**: Validation checks from tasks are preserved

Example workflow:

```python
# 1. Generate plan using DECOMPOSITION.md
plan = orchestrator._generate_decomposition_plan("Build a web app")

# 2. Create coordinator with plan
coordinator = AgentTeamCoordinator("web_app_team")
coordinator.create_dynamic_plan("Build a web app", plan["atomic_tasks"])

# 3. Spawn agents for each task
for task in plan["atomic_tasks"]:
    role = orchestrator._determine_role(task["action"], task.get("tool_or_endpoint", ""))
    agent_type = orchestrator._select_agent_type(task)
    coordinator.spawn_agent(agent_type, role, task["task_id"])

# 4. Wait and collect results
coordinator.wait_for_completion()
results = coordinator.get_results()
```

## Error Handling

### Task Failure

When a task fails:
1. Agent writes failure status to `status.json`
2. Coordinator broadcasts failure to team
3. Dependent tasks remain blocked
4. Orchestrator can decide to retry or escalate

### Agent Crash

When an agent crashes:
1. Coordinator detects via process check
2. Task status updated to "failed"
3. Message sent to orchestrator
4. Can spawn replacement agent if needed

### Recovery

Teams can be resumed from checkpoints:

```python
# Save checkpoint
coordinator.save_checkpoint()

# Later, resume
coordinator = AgentTeamCoordinator.load_from_checkpoint(Path("workflows/team_id"))
```

## Best Practices

1. **Team Size**: Start with 3-5 agents. Too many increases coordination overhead.

2. **Task Size**: Tasks should be self-contained with clear deliverables.

3. **Dependencies**: Minimize dependencies to maximize parallelism.

4. **Timeouts**: Always set reasonable timeouts to prevent hung agents.

5. **Validation**: Include validation checks in atomic tasks.

6. **Plan Mode**: Use plan mode for complex or risky changes.

7. **Monitoring**: Regularly check `team status` during long runs.

## Examples

### Example 1: Code Review Team

```bash
python cli.py team create \
  --request "Review the authentication module for security issues" \
  --team-id auth_review \
  --max-parallel 3

# Spawns:
# - security_reviewer (Claude Code)
# - code_quality_reviewer (OpenCode)
# - test_coverage_reviewer (LangChain)
```

### Example 2: Feature Implementation

```python
orchestrator.orchestrate_team(
    user_request="""
    Implement a user authentication system with:
    - JWT token generation
    - Password hashing
    - Login/logout endpoints
    - Unit tests
    """,
    team_id="auth_feature",
    max_parallel=4,
)

# Spawns parallel agents:
# - tech_lead: Design architecture
# - developer_1: Implement JWT
# - developer_2: Implement password hashing
# - qa_engineer: Write tests
```

### Example 3: Research Task

```python
# Research task uses LangChain subagents for speed
orchestrator.orchestrate_team(
    user_request="Research the top 5 Python web frameworks and compare them",
    team_id="framework_research",
    max_parallel=5,
)
```

## Troubleshooting

### Agents Not Spawning

Check that the CLI tools are installed:
```bash
which opencode
which claude
```

### Tasks Stuck in "blocked"

Check dependency chain in task_board.json. Ensure dependencies complete first.

### Messages Not Received

Verify message file permissions and JSON format.

### High Token Usage

LangChain subagents are cheaper but less capable. Use them for simple tasks.

## Future Enhancements

- [ ] Dynamic role assignment based on task complexity
- [ ] Agent-to-agent direct messaging (bypass coordinator)
- [ ] Automatic retry with exponential backoff
- [ ] Cost tracking per team/agent
- [ ] Web UI for monitoring teams
- [ ] Integration with more agent types (GitHub Copilot, etc.)
