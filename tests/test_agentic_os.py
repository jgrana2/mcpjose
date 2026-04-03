"""Tests for Agentic OS - Agent Team components."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent_team import (
    AgentTeamCoordinator,
    AgentType,
    MessageBus,
    Task,
    TaskBoard,
    TaskStatus,
)
from core.agent_team.adapter import AgentInstance, AgentStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_work_dir():
    """Provide a temporary working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_atomic_task():
    """Provide a sample atomic task."""
    return {
        "task_id": "1.1.1",
        "parent_id": "1.1",
        "depth": 2,
        "action": "Extract pricing data from document",
        "exact_inputs": ["path:userapp/BusinessDescription.md"],
        "exact_outputs": ["pricing_data.json"],
        "tool_or_endpoint": "read_file",
        "validation_check": "Data is valid JSON",
        "retry_policy": {"max_attempts": 2, "backoff_seconds": [1]},
        "failure_mode": "ask-user",
    }


@pytest.fixture
def sample_plan_dir(temp_work_dir, sample_atomic_task):
    """Create a sample plan directory with AtomicTasks.json."""
    plan_dir = temp_work_dir / "Plan"
    plan_dir.mkdir()

    atomic_tasks = {"atomic_tasks": [sample_atomic_task]}
    with open(plan_dir / "AtomicTasks.json", "w") as f:
        json.dump(atomic_tasks, f)

    task_tree = {
        "nodes": [
            {"id": "1", "parent_id": None, "depth": 0, "depends_on": []},
            {"id": "1.1", "parent_id": "1", "depth": 1, "depends_on": []},
            {"id": "1.1.1", "parent_id": "1.1", "depth": 2, "depends_on": []},
        ]
    }
    with open(plan_dir / "TaskTree.json", "w") as f:
        json.dump(task_tree, f)

    return plan_dir


# ---------------------------------------------------------------------------
# TaskBoard Tests
# ---------------------------------------------------------------------------


class TestTaskBoard:
    """Tests for TaskBoard state management."""

    def test_create_and_add_task(self, temp_work_dir):
        board = TaskBoard(temp_work_dir / "board.json")
        task = Task(
            task_id="1.1.1",
            parent_id="1.1",
            depth=2,
            action="Test task",
        )
        board.add_task(task)

        loaded = board.get_task("1.1.1")
        assert loaded is not None
        assert loaded.action == "Test task"

    def test_claim_task(self, temp_work_dir):
        board = TaskBoard(temp_work_dir / "board.json")
        task = Task(
            task_id="1.1.1",
            parent_id="1.1",
            depth=2,
            action="Test task",
            dependencies=[],
        )
        board.add_task(task)

        claimed = board.claim_task("agent_001", "1.1.1")
        assert claimed is not None
        assert claimed.assigned_to == "agent_001"
        assert claimed.status == TaskStatus.IN_PROGRESS

    def test_claim_task_with_dependencies(self, temp_work_dir):
        board = TaskBoard(temp_work_dir / "board.json")

        # Add dependency task
        dep_task = Task(
            task_id="1.1.1",
            parent_id="1.1",
            depth=2,
            action="Dependency task",
            dependencies=[],
        )
        board.add_task(dep_task)

        # Add dependent task
        task = Task(
            task_id="1.1.2",
            parent_id="1.1",
            depth=2,
            action="Dependent task",
            dependencies=["1.1.1"],
        )
        board.add_task(task)

        # Try to claim before dependency is done
        claimed = board.claim_task("agent_001", "1.1.2")
        assert claimed is None  # Blocked

        # Complete dependency
        board.update_task_status("1.1.1", TaskStatus.COMPLETED)

        # Now can claim
        claimed = board.claim_task("agent_001", "1.1.2")
        assert claimed is not None

    def test_progress_tracking(self, temp_work_dir):
        board = TaskBoard(temp_work_dir / "board.json")

        for i in range(3):
            board.add_task(
                Task(
                    task_id=f"task_{i}",
                    parent_id=None,
                    depth=1,
                    action=f"Task {i}",
                )
            )

        progress = board.get_progress()
        assert progress["total"] == 3
        assert progress["completed"] == 0

        board.update_task_status("task_0", TaskStatus.COMPLETED)
        board.update_task_status("task_1", TaskStatus.FAILED)

        progress = board.get_progress()
        assert progress["completed"] == 1
        assert progress["failed"] == 1


# ---------------------------------------------------------------------------
# MessageBus Tests
# ---------------------------------------------------------------------------


class TestMessageBus:
    """Tests for MessageBus inter-agent communication."""

    def test_send_and_receive_message(self, temp_work_dir):
        bus = MessageBus(temp_work_dir / "messages.json")

        msg_id = bus.send_message(
            from_agent="agent_001",
            to_agent="agent_002",
            message_type="instruction",
            content={"text": "Complete task 1.1.1"},
        )

        assert msg_id is not None

        messages = bus.get_messages_for_agent("agent_002")
        assert len(messages) == 1
        assert messages[0]["content"]["text"] == "Complete task 1.1.1"

    def test_broadcast(self, temp_work_dir):
        bus = MessageBus(temp_work_dir / "messages.json")

        bus.broadcast(
            from_agent="coordinator",
            message_type="status",
            content={"status": "starting"},
        )

        # Both agents should receive
        messages1 = bus.get_messages_for_agent("agent_001")
        messages2 = bus.get_messages_for_agent("agent_002")

        assert len(messages1) == 1
        assert len(messages2) == 1

    def test_conversation(self, temp_work_dir):
        bus = MessageBus(temp_work_dir / "messages.json")

        bus.send_message("agent_001", "agent_002", "question", {"text": "Help?"})
        bus.send_message("agent_002", "agent_001", "answer", {"text": "Sure!"})
        bus.send_message("agent_001", "agent_002", "thanks", {"text": "Thanks!"})

        conv = bus.get_conversation("agent_001", "agent_002")
        assert len(conv) == 3


# ---------------------------------------------------------------------------
# AgentTeamCoordinator Tests
# ---------------------------------------------------------------------------


class TestAgentTeamCoordinator:
    """Tests for AgentTeamCoordinator."""

    def test_initialize_from_plan(self, temp_work_dir, sample_plan_dir):
        coordinator = AgentTeamCoordinator("test_team", temp_work_dir)

        # Mock adapters
        mock_adapter = MagicMock()
        mock_adapter.agent_type = AgentType.LANGCHAIN_SUBAGENT
        coordinator.register_adapter(mock_adapter)

        coordinator.initialize_from_plan(sample_plan_dir)

        # Check tasks were loaded
        tasks = coordinator.task_board.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == "1.1.1"

    def test_spawn_agent(self, temp_work_dir, sample_atomic_task):
        coordinator = AgentTeamCoordinator("test_team", temp_work_dir)

        # Add task first
        coordinator.task_board.add_task(Task.from_dict(sample_atomic_task))

        # Mock adapter - return agent with whatever ID coordinator generates
        mock_adapter = MagicMock()
        mock_adapter.agent_type = AgentType.LANGCHAIN_SUBAGENT

        def mock_spawn(agent_id, role, task, work_dir, **kwargs):
            return AgentInstance(
                agent_id=agent_id,  # Use the ID passed by coordinator
                agent_type=AgentType.LANGCHAIN_SUBAGENT,
                role=role,
                pid=None,
                work_dir=work_dir,
                status=AgentStatus.RUNNING,
                started_at=__import__("datetime").datetime.now(),
            )

        mock_adapter.spawn.side_effect = mock_spawn
        coordinator.register_adapter(mock_adapter)

        # Spawn agent
        agent = coordinator.spawn_agent(
            AgentType.LANGCHAIN_SUBAGENT,
            "tester",
            "1.1.1",
        )

        assert agent.role == "tester"
        assert agent.agent_type == AgentType.LANGCHAIN_SUBAGENT

        # Verify task was claimed with the coordinator-generated ID
        task = coordinator.task_board.get_task("1.1.1")
        assert task.assigned_to == agent.agent_id  # Should match the returned agent

    def test_progress_tracking(self, temp_work_dir, sample_atomic_task):
        coordinator = AgentTeamCoordinator("test_team", temp_work_dir)
        coordinator.task_board.add_task(Task.from_dict(sample_atomic_task))

        progress = coordinator.get_progress()
        assert progress["tasks"]["total"] == 1
        assert progress["tasks"]["pending"] == 1


# ---------------------------------------------------------------------------
# Adapter Tests
# ---------------------------------------------------------------------------


class TestLangChainSubagentAdapter:
    """Tests for LangChainSubagentAdapter."""

    def test_spawn_and_execute(self, temp_work_dir):
        from tools.agent_spawner.langchain_adapter import LangChainSubagentAdapter

        adapter = LangChainSubagentAdapter()

        task = {
            "task_id": "1.1.1",
            "action": "Search for Python documentation",
            "tool_or_endpoint": "search",
        }

        agent = adapter.spawn(
            agent_id="lc_001",
            role="researcher",
            task=task,
            work_dir=temp_work_dir / "lc_001",
        )

        assert agent.agent_type == AgentType.LANGCHAIN_SUBAGENT
        assert agent.role == "researcher"

        # Wait for thread to complete
        time.sleep(0.5)

        # Check status
        status = adapter.check_status(agent)
        assert status in (AgentStatus.COMPLETED, AgentStatus.RUNNING)


# ---------------------------------------------------------------------------
# Tool Integration Tests
# ---------------------------------------------------------------------------


class TestAgentSpawnerTools:
    """Tests for agent spawner tools."""

    def test_spawn_agent_tool(self, temp_work_dir, sample_atomic_task):
        from tools.agent_spawner import spawn_agent

        # First create a coordinator with the task
        coordinator = AgentTeamCoordinator("test_team", temp_work_dir)
        coordinator.task_board.add_task(Task.from_dict(sample_atomic_task))

        # Mock the adapter
        with patch("tools.agent_spawner.tools._get_coordinator") as mock_get:
            mock_coordinator = MagicMock()
            mock_agent = MagicMock()
            mock_agent.agent_id = "lc_001"
            mock_agent.agent_type = AgentType.LANGCHAIN_SUBAGENT
            mock_agent.role = "tester"
            mock_agent.status.value = "running"
            mock_agent.work_dir = temp_work_dir / "lc_001"
            mock_coordinator.spawn_agent.return_value = mock_agent
            mock_get.return_value = mock_coordinator

            result = spawn_agent(
                team_id="test_team",
                agent_type="langchain_subagent",
                role="tester",
                task_id="1.1.1",
                work_dir=str(temp_work_dir),
            )

            assert result["success"] is True
            assert result["agent_id"] == "lc_001"


# ---------------------------------------------------------------------------
# End-to-End Tests
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """End-to-end tests for complete workflow."""

    def test_simple_team_workflow(self, temp_work_dir, sample_plan_dir):
        """Test a simple team execution from plan to completion."""
        from tools.agent_spawner import spawn_agent_team, get_team_status

        # Mock coordinator behavior for speed
        with patch("tools.agent_spawner.tools.AgentTeamCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coord_cls.return_value = mock_coordinator

            mock_coordinator.task_board.get_all_tasks.return_value = [
                Task.from_dict(
                    {
                        "task_id": "1.1.1",
                        "action": "Test task",
                        "tool_or_endpoint": "call_llm",
                    }
                )
            ]

            result = spawn_agent_team(
                team_id="e2e_test",
                plan_dir=str(sample_plan_dir),
                work_dir=str(temp_work_dir),
                max_parallel=1,
            )

            assert result["success"] is True
            mock_coordinator.initialize_from_plan.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
