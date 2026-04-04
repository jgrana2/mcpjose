"""Agent Team Coordinator for Agentic OS.

The central coordinator that manages a cross-functional team of agents.
Uses shared JSON files for state management and coordination.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from core.workflow_state import WorkflowStateManager

from .adapter import AgentAdapter, AgentInstance, AgentStatus, AgentType
from .state import MessageBus, Task, TaskBoard, TaskStatus


class AgentTeamCoordinator:
    """Coordinates a team of agents working together on a workflow.

    This is the central hub that:
    1. Manages the shared task board (JSON-based)
    2. Handles inter-agent messaging (JSON-based)
    3. Tracks agent lifecycle
    4. Synthesizes results
    5. Provides checkpoint/resume capability

    Usage:
        coordinator = AgentTeamCoordinator("team_123", Path("workflows/team_123"))
        coordinator.initialize_from_plan(Path("userapp/Plan"))
        coordinator.spawn_agent(AgentType.OPENCODE, "business_analyst", task)
        coordinator.wait_for_completion()
        results = coordinator.get_results()
    """

    def __init__(
        self,
        team_id: str,
        work_dir: Path,
        state_manager: Optional[WorkflowStateManager] = None,
    ):
        self.team_id = team_id
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Initialize shared state
        self.task_board = TaskBoard(self.work_dir / "task_board.json")
        self.message_bus = MessageBus(self.work_dir / "messages.json")
        self.state_manager = state_manager or WorkflowStateManager(self.work_dir)

        # Agent registry
        self._adapters: Dict[AgentType, AgentAdapter] = {}
        self._agents: Dict[str, AgentInstance] = {}

        # Create subdirectories
        (self.work_dir / "artifacts").mkdir(exist_ok=True)
        (self.work_dir / "logs").mkdir(exist_ok=True)

    def register_adapter(self, adapter: AgentAdapter) -> None:
        """Register an adapter for an agent type."""
        self._adapters[adapter.agent_type] = adapter

    def initialize_from_plan(self, plan_dir: Path) -> None:
        """Initialize the team from a DECOMPOSITION.md plan directory.

        Loads TaskTree.json and AtomicTasks.json to populate the task board.
        """
        plan_path = Path(plan_dir)

        # Load AtomicTasks.json
        atomic_tasks_path = plan_path / "AtomicTasks.json"
        if not atomic_tasks_path.exists():
            raise FileNotFoundError(f"AtomicTasks.json not found in {plan_dir}")

        with open(atomic_tasks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            atomic_tasks = data.get("atomic_tasks", [])

        # Load TaskTree.json for dependencies
        task_tree_path = plan_path / "TaskTree.json"
        dependencies = {}
        if task_tree_path.exists():
            with open(task_tree_path, "r", encoding="utf-8") as f:
                tree_data = json.load(f)
                for node in tree_data.get("nodes", []):
                    node_id = node.get("id")
                    deps = node.get("depends_on", [])
                    if node_id and deps:
                        dependencies[node_id] = deps

        # Create tasks
        tasks = []
        for task_data in atomic_tasks:
            task_id = task_data["task_id"]
            task = Task(
                task_id=task_id,
                parent_id=task_data.get("parent_id"),
                depth=task_data.get("depth", 0),
                action=task_data["action"],
                exact_inputs=task_data.get("exact_inputs", []),
                exact_outputs=task_data.get("exact_outputs", []),
                tool_or_endpoint=task_data.get("tool_or_endpoint", ""),
                validation_check=task_data.get("validation_check", ""),
                retry_policy=task_data.get("retry_policy", {}),
                failure_mode=task_data.get("failure_mode", "ask-user"),
                dependencies=dependencies.get(task_id, []),
                branch_alternatives=task_data.get("branch_alternatives", []),
                backtrack_policy=task_data.get("backtrack_policy", {}),
            )
            tasks.append(task)

        # Add all tasks to board
        self.task_board.add_tasks(tasks)

        # Create team config
        self._save_team_config(
            {
                "team_id": self.team_id,
                "created_at": datetime.now().isoformat(),
                "status": "initialized",
                "plan_dir": str(plan_path),
                "total_tasks": len(tasks),
            }
        )

    def create_dynamic_plan(
        self,
        user_request: str,
        atomic_tasks: List[Dict[str, Any]],
    ) -> None:
        """Create a plan dynamically from the orchestrator.

        Used when the LangChain agent generates a plan on-the-fly
        rather than loading from the Plan/ folder.
        """
        tasks = []
        for task_data in atomic_tasks:
            task = Task(
                task_id=task_data["task_id"],
                parent_id=task_data.get("parent_id"),
                depth=task_data.get("depth", 0),
                action=task_data["action"],
                exact_inputs=task_data.get("exact_inputs", []),
                exact_outputs=task_data.get("exact_outputs", []),
                tool_or_endpoint=task_data.get("tool_or_endpoint", ""),
                validation_check=task_data.get("validation_check", ""),
                retry_policy=task_data.get("retry_policy", {}),
                failure_mode=task_data.get("failure_mode", "ask-user"),
                dependencies=task_data.get("dependencies", []),
            )
            tasks.append(task)

        self.task_board.add_tasks(tasks)

        self._save_team_config(
            {
                "team_id": self.team_id,
                "created_at": datetime.now().isoformat(),
                "status": "initialized",
                "user_request": user_request,
                "total_tasks": len(tasks),
            }
        )

    def spawn_agent(
        self,
        agent_type: AgentType,
        role: str,
        task_id: str,
        **kwargs: Any,
    ) -> AgentInstance:
        """Spawn a new agent to work on a task.

        Args:
            agent_type: Type of agent to spawn.
            role: The role this agent plays (e.g., "business_analyst").
            task_id: The task to assign to this agent.
            **kwargs: Additional options passed to the adapter.

        Returns:
            The spawned AgentInstance.
        """
        if agent_type not in self._adapters:
            raise ValueError(f"No adapter registered for {agent_type.value}")

        # Get the task
        task = self.task_board.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Generate agent ID
        agent_id = f"{agent_type.value}_{role}_{int(datetime.now().timestamp())}"

        # Create agent work directory
        agent_work_dir = self.work_dir / "artifacts" / agent_id
        agent_work_dir.mkdir(parents=True, exist_ok=True)

        # Spawn via adapter
        adapter = self._adapters[agent_type]
        agent = adapter.spawn(
            agent_id=agent_id,
            role=role,
            task=task.to_dict(),
            work_dir=agent_work_dir,
            on_complete=self._on_agent_complete,
            **kwargs,
        )

        # Register agent
        self._agents[agent_id] = agent

        # Claim task for this agent
        self.task_board.claim_task(agent_id, task_id)

        # Notify team
        self.message_bus.broadcast(
            from_agent="coordinator",
            message_type="agent_spawned",
            content={
                "agent_id": agent_id,
                "agent_type": agent_type.value,
                "role": role,
                "task_id": task_id,
            },
        )

        # Update team config
        self._update_team_config(
            {
                "agents": list(self._agents.keys()),
            }
        )

        return agent

    def _on_agent_complete(
        self, agent_id: str, task_id: str, result: Dict[str, Any]
    ) -> None:
        """Callback when an agent completes its task."""
        status = result.get("status", "completed")
        if status == "completed":
            self.complete_task(agent_id, task_id, result)
        else:
            error_msg = result.get("error", "Task failed")
            self.fail_task(agent_id, task_id, error_msg)

    def spawn_agents_parallel(
        self,
        spawns: List[Dict[str, Any]],
    ) -> List[AgentInstance]:
        """Spawn multiple agents in parallel.

        Args:
            spawns: List of spawn configurations, each with:
                - agent_type
                - role
                - task_id
                - **kwargs

        Returns:
            List of spawned AgentInstances.
        """
        import concurrent.futures

        agents = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(spawns)) as executor:
            futures = []
            for spawn_config in spawns:
                future = executor.submit(
                    self.spawn_agent,
                    spawn_config["agent_type"],
                    spawn_config["role"],
                    spawn_config["task_id"],
                    **spawn_config.get("kwargs", {}),
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    agent = future.result()
                    agents.append(agent)
                except Exception as e:
                    # Log error but continue
                    print(f"Failed to spawn agent: {e}")

        return agents

    def check_agent_status(self, agent_id: str) -> AgentStatus:
        """Check the status of an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        adapter = self._adapters.get(agent.agent_type)
        if not adapter:
            return agent.status

        status = adapter.check_status(agent)

        # Update cached status
        if status != agent.status:
            agent.status = status
            if status in (AgentStatus.COMPLETED, AgentStatus.FAILED):
                agent.completed_at = datetime.now()

        return status

    def check_all_agents(self) -> Dict[str, AgentStatus]:
        """Check status of all agents."""
        return {
            agent_id: self.check_agent_status(agent_id) for agent_id in self._agents
        }

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
    ) -> str:
        """Send a message between agents."""
        return self.message_bus.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
        )

    def get_messages(
        self,
        agent_id: str,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get messages for an agent."""
        return self.message_bus.get_messages_for_agent(
            agent_id=agent_id,
            unread_only=unread_only,
        )

    def complete_task(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Mark a task as completed by an agent."""
        # Update task status
        self.task_board.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=result,
        )

        # Notify team
        self.message_bus.broadcast(
            from_agent=agent_id,
            message_type="task_completed",
            content={
                "task_id": task_id,
                "agent_id": agent_id,
                "result_summary": result.get("summary", "Task completed"),
            },
        )

        # Try to save artifacts
        agent = self._agents.get(agent_id)
        if agent:
            adapter = self._adapters.get(agent.agent_type)
            if adapter:
                try:
                    output = adapter.get_output(agent)
                    artifacts_dir = self.work_dir / "artifacts" / agent_id
                    artifacts_dir.mkdir(exist_ok=True)
                    with open(
                        artifacts_dir / "output.json", "w", encoding="utf-8"
                    ) as f:
                        json.dump(output, f, indent=2, default=str)
                except Exception as e:
                    print(f"Failed to save artifacts for {agent_id}: {e}")

    def fail_task(
        self,
        agent_id: str,
        task_id: str,
        error_message: str,
    ) -> None:
        """Mark a task as failed."""
        self.task_board.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=error_message,
        )

        self.message_bus.broadcast(
            from_agent=agent_id,
            message_type="task_failed",
            content={
                "task_id": task_id,
                "agent_id": agent_id,
                "error": error_message,
            },
        )

    def get_next_task(self, agent_capabilities: List[str]) -> Optional[Task]:
        """Get the next available task matching agent capabilities."""
        # Simple implementation - return next pending task
        # Could be enhanced to match capabilities with task requirements
        return self.task_board.get_next_available_task()

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress."""
        task_progress = self.task_board.get_progress()
        agent_statuses = self.check_all_agents()

        return {
            "team_id": self.team_id,
            "tasks": task_progress,
            "agents": {
                agent_id: status.value for agent_id, status in agent_statuses.items()
            },
        }

    def wait_for_completion(
        self,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Wait for all tasks to complete.

        Args:
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait (None = forever).
            verbose: If True, print progress updates.

        Returns:
            Final progress summary.
        """
        import time

        start_time = time.time()
        last_progress = None

        while True:
            progress = self.get_progress()
            tasks = progress["tasks"]

            # Print progress if changed and verbose
            if verbose and tasks != last_progress:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Progress: {tasks['completed']}/{tasks['total']} completed, "
                    f"{tasks.get('in_progress', 0)} in_progress, "
                    f"{tasks.get('pending', 0)} pending"
                    + (
                        f", {tasks['failed']} failed"
                        if tasks.get("failed", 0) > 0
                        else ""
                    )
                )
                last_progress = tasks.copy()

            # Check if done
            if tasks["completed"] + tasks["failed"] >= tasks["total"]:
                if verbose:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"All tasks completed. {tasks['completed']}/{tasks['total']} done, "
                        f"{tasks['failed']} failed."
                    )
                break

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                if verbose:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Timeout reached.")
                break

            time.sleep(poll_interval)

        return self.get_progress()

    def shutdown_all(self, graceful: bool = True) -> None:
        """Shutdown all agents."""
        for agent_id, agent in self._agents.items():
            adapter = self._adapters.get(agent.agent_type)
            if adapter:
                try:
                    adapter.shutdown(agent, graceful=graceful)
                except Exception as e:
                    print(f"Failed to shutdown {agent_id}: {e}")

        self._update_team_config({"status": "shutdown"})

    def get_results(self) -> Dict[str, Any]:
        """Get final results from all completed tasks."""
        all_tasks = self.task_board.get_all_tasks()
        completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]

        return {
            "team_id": self.team_id,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completed_tasks": [t.to_dict() for t in completed],
            "failed_tasks": [t.to_dict() for t in failed],
            "artifacts_dir": str(self.work_dir / "artifacts"),
        }

    def save_checkpoint(self) -> Path:
        """Save a checkpoint for resumption."""
        checkpoint = {
            "team_id": self.team_id,
            "timestamp": datetime.now().isoformat(),
            "agents": {aid: a.to_dict() for aid, a in self._agents.items()},
            "tasks": [t.to_dict() for t in self.task_board.get_all_tasks()],
        }

        checkpoint_file = self.work_dir / "checkpoint.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, default=str)

        return checkpoint_file

    def _save_team_config(self, config: Dict[str, Any]) -> None:
        """Save team configuration."""
        config_file = self.work_dir / "team_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, default=str)

    def _update_team_config(self, updates: Dict[str, Any]) -> None:
        """Update team configuration."""
        config_file = self.work_dir / "team_config.json"
        config = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        config.update(updates)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, default=str)

    @classmethod
    def load_from_checkpoint(cls, work_dir: Path) -> "AgentTeamCoordinator":
        """Load a team from a checkpoint."""
        checkpoint_file = work_dir / "checkpoint.json"
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"No checkpoint found in {work_dir}")

        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)

        team_id = checkpoint["team_id"]
        coordinator = cls(team_id, work_dir)

        # Restore tasks
        for task_data in checkpoint.get("tasks", []):
            coordinator.task_board.add_task(Task.from_dict(task_data))

        return coordinator
