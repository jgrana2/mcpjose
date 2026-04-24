"""Agent spawning tools for ProjectToolRegistry.

These tools allow the LangChain agent to spawn and manage agent teams.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from core.agent_team import Task

from core.agent_team import AgentTeamCoordinator, AgentType
from tools.agent_spawner.claude_code_adapter import ClaudeCodeAdapter
from tools.agent_spawner.langchain_adapter import LangChainSubagentAdapter
from tools.agent_spawner.opencode_adapter import OpenCodeAdapter


# Global coordinator cache (team_id -> coordinator)
_coordinators: Dict[str, AgentTeamCoordinator] = {}


def _get_coordinator(
    team_id: str,
    work_dir: Optional[str] = None,
) -> AgentTeamCoordinator:
    """Get or create a coordinator for a team."""
    if team_id not in _coordinators:
        work_path = Path(work_dir) if work_dir else Path(f"workflows/{team_id}")
        coordinator = AgentTeamCoordinator(team_id, work_path)

        # Register adapters
        try:
            coordinator.register_adapter(OpenCodeAdapter())
        except RuntimeError:
            pass  # OpenCode not installed

        try:
            coordinator.register_adapter(ClaudeCodeAdapter())
        except RuntimeError:
            pass  # Claude Code not installed

        coordinator.register_adapter(LangChainSubagentAdapter())

        _coordinators[team_id] = coordinator

    return _coordinators[team_id]


def spawn_agent(
    team_id: str,
    agent_type: str,
    role: str,
    task_id: Optional[str] = None,
    action: Optional[str] = None,
    work_dir: Optional[str] = None,
    plan_mode: bool = True,
    timeout_minutes: int = 30,
) -> Dict[str, Any]:
    """Spawn a new agent in a team to work on a task.

    Args:
        team_id: Unique identifier for the team.
        agent_type: Type of agent to spawn ("opencode", "claude_code", "langchain_subagent").
        role: Role this agent plays (e.g., "business_analyst", "tech_lead", "qa_engineer").
        task_id: The task ID from the task board. If not provided, a task will be created.
        action: The action/description for a new task. Required if task_id not provided.
        work_dir: Directory for team state (default: workflows/{team_id}).
        plan_mode: If True, spawn in plan mode for safety.
        timeout_minutes: Maximum time agent can run.

    Returns:
        Dictionary with agent_id, status, and work_dir.

    Example:
        spawn_agent(
            team_id="project_alpha",
            agent_type="opencode",
            role="developer",
            action="Fix bug in auth.py",
        )
    """
    try:
        agent_type_enum = AgentType(agent_type)
    except ValueError:
        return {
            "success": False,
            "error": f"Unknown agent_type: {agent_type}. "
            f"Valid types: {[t.value for t in AgentType]}",
        }

    try:
        coordinator = _get_coordinator(team_id, work_dir)

        # Create task on-the-fly if action provided or task_id not found
        if action:
            from core.agent_team import Task

            if not task_id:
                task_id = f"task_{int(datetime.now().timestamp())}"
            task = Task(
                task_id=task_id,
                action=action,
                depth=0,
                parent_id=None,
            )
            try:
                coordinator.task_board.add_task(task)
            except ValueError:
                pass  # Task already exists

        agent = coordinator.spawn_agent(
            agent_type=agent_type_enum,
            role=role,
            task_id=task_id,
            plan_mode=plan_mode,
            timeout_minutes=timeout_minutes,
        )

        return {
            "success": True,
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type.value,
            "role": agent.role,
            "status": agent.status.value,
            "work_dir": str(agent.work_dir),
            "task_id": task_id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def spawn_agent_team(
    team_id: str,
    plan_dir: str,
    work_dir: Optional[str] = None,
    max_parallel: int = 5,
) -> Dict[str, Any]:
    """Spawn a complete team from a DECOMPOSITION.md plan.

    Reads AtomicTasks.json and creates agents for each task based on role.

    Args:
        team_id: Unique identifier for the team.
        plan_dir: Directory containing AtomicTasks.json and TaskTree.json.
        work_dir: Directory for team state.
        max_parallel: Maximum number of agents to spawn in parallel.

    Returns:
        Dictionary with team status and spawned agents.

    Example:
        spawn_agent_team(
            team_id="project_alpha",
            plan_dir="userapp/Plan",
            max_parallel=3,
        )
    """
    try:
        coordinator = _get_coordinator(team_id, work_dir)
        coordinator.initialize_from_plan(Path(plan_dir))

        # Determine role assignments based on task content
        tasks = coordinator.task_board.get_all_tasks()

        spawned = []
        for task in tasks[:max_parallel]:
            # Simple role assignment based on task content
            role = _determine_role(task.action, task.tool_or_endpoint)
            agent_type = _determine_agent_type(task)

            try:
                agent = coordinator.spawn_agent(agent_type, role, task.task_id)
                spawned.append(
                    {
                        "agent_id": agent.agent_id,
                        "role": role,
                        "task_id": task.task_id,
                    }
                )
            except Exception as e:
                spawned.append(
                    {
                        "task_id": task.task_id,
                        "error": str(e),
                    }
                )

        return {
            "success": True,
            "team_id": team_id,
            "total_tasks": len(tasks),
            "spawned_agents": len([s for s in spawned if "agent_id" in s]),
            "agents": spawned,
            "work_dir": str(coordinator.work_dir),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_team_status(team_id: str, work_dir: Optional[str] = None) -> Dict[str, Any]:
    """Get the status of an agent team.

    Args:
        team_id: The team identifier.
        work_dir: Directory for team state.

    Returns:
        Dictionary with task progress and agent statuses.
    """
    try:
        coordinator = _get_coordinator(team_id, work_dir)
        return {
            "success": True,
            **coordinator.get_progress(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def send_message_to_agent(
    team_id: str,
    from_agent: str,
    to_agent: str,
    message_type: str,
    content: str,
    work_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to an agent in a team.

    Args:
        team_id: The team identifier.
        from_agent: Sender agent ID (use "coordinator" for system messages).
        to_agent: Recipient agent ID (use "broadcast" for all agents).
        message_type: Type of message (instruction, question, answer, status).
        content: Message content.
        work_dir: Directory for team state.

    Returns:
        Dictionary with message_id and status.
    """
    try:
        coordinator = _get_coordinator(team_id, work_dir)
        message_id = coordinator.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content={"text": content},
        )

        return {
            "success": True,
            "message_id": message_id,
            "from": from_agent,
            "to": to_agent,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def wait_for_team(
    team_id: str,
    poll_interval: float = 5.0,
    timeout: Optional[float] = None,
    work_dir: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Wait for all tasks in a team to complete.

    Args:
        team_id: The team identifier.
        poll_interval: Seconds between status checks.
        timeout: Maximum seconds to wait (None = forever).
        work_dir: Directory for team state.
        verbose: If True, print progress updates.

    Returns:
            Dictionary with final results.
    """
    try:
        coordinator = _get_coordinator(team_id, work_dir)
        progress = coordinator.wait_for_completion(
            poll_interval, timeout, verbose=verbose
        )
        results = coordinator.get_results()

        return {
            "success": True,
            "progress": progress,
            "results": results,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def shutdown_team(
    team_id: str,
    graceful: bool = True,
    work_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Shutdown all agents in a team.

    Args:
        team_id: The team identifier.
        graceful: If True, try graceful shutdown first.
        work_dir: Directory for team state.

    Returns:
        Dictionary with shutdown status.
    """
    try:
        coordinator = _get_coordinator(team_id, work_dir)
        coordinator.shutdown_all(graceful=graceful)

        return {
            "success": True,
            "team_id": team_id,
            "status": "shutdown",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _determine_role(action: str, tool_or_endpoint: str) -> str:
    """Determine agent role based on task content."""
    action_lower = action.lower()
    tool_lower = tool_or_endpoint.lower()

    if any(
        word in action_lower
        for word in ["business", "requirements", "stakeholder", "analysis"]
    ):
        return "business_analyst"
    if any(
        word in action_lower
        for word in ["code", "implement", "develop", "refactor", "architecture"]
    ):
        return "tech_lead"
    if any(
        word in action_lower for word in ["test", "qa", "validate", "verify", "quality"]
    ):
        return "qa_engineer"
    if any(
        word in action_lower
        for word in ["deploy", "infra", "pipeline", "devops", "ci/cd"]
    ):
        return "devops_engineer"
    if any(
        word in action_lower
        for word in ["research", "investigate", "explore", "analyze data"]
    ):
        return "researcher"
    if any(
        word in action_lower
        for word in ["design", "ux", "ui", "interface", "user experience"]
    ):
        return "ux_designer"

    # Default based on tool
    if "code" in tool_lower or "implement" in tool_lower:
        return "developer"

    return "generalist"


def _determine_agent_type(task: Task) -> AgentType:
    """Determine which agent type to use for a task."""
    action = task.action.lower()
    tool = task.tool_or_endpoint.lower()

    # Complex development tasks -> OpenCode or Claude Code
    if any(
        word in action for word in ["implement", "refactor", "code review", "build"]
    ):
        # Prefer Claude Code if available, else OpenCode
        try:
            ClaudeCodeAdapter()
            return AgentType.CLAUDE_CODE
        except RuntimeError:
            try:
                OpenCodeAdapter()
                return AgentType.OPENCODE
            except RuntimeError:
                return AgentType.LANGCHAIN_SUBAGENT

    # Quick research or LLM tasks -> LangChain subagent
    if any(
        word in action for word in ["research", "summarize", "analyze", "generate text"]
    ):
        return AgentType.LANGCHAIN_SUBAGENT

    # File operations -> LangChain subagent (faster)
    if any(word in tool for word in ["read", "write", "file"]):
        return AgentType.LANGCHAIN_SUBAGENT

    # Default to LangChain subagent for safety
    return AgentType.LANGCHAIN_SUBAGENT

