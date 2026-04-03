"""Tests for the workflow executor and state management."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.workflow_state import WorkflowStateManager
from mcp_server.workflow_executor import BasicWorkflowExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_TASK = {
    "task_id": "1.1.1",
    "parent_id": "1.1",
    "depth": 2,
    "action": "Read business description",
    "exact_inputs": ["path:userapp/BusinessDescription.md"],
    "exact_outputs": ["internal model"],
    "tool_or_endpoint": "File read + deterministic parsing",
    "validation_check": "Assert data exists",
    "retry_policy": {"max_attempts": 1, "backoff_seconds": []},
    "failure_mode": "ask-user",
}


def _make_atomic_tasks_json(tasks: list) -> str:
    return json.dumps({"atomic_tasks": tasks})


def _make_plan_dir(tmp_path: Path, tasks: list | None = None) -> Path:
    plan_dir = tmp_path / "Plan"
    plan_dir.mkdir()
    task_list = tasks if tasks is not None else [MINIMAL_TASK]
    (plan_dir / "AtomicTasks.json").write_text(_make_atomic_tasks_json(task_list))
    return plan_dir


# ---------------------------------------------------------------------------
# WorkflowStateManager tests
# ---------------------------------------------------------------------------


def test_state_manager_create_and_load(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    state = manager.create_state("wf1", [MINIMAL_TASK])

    assert state["workflow_id"] == "wf1"
    assert state["status"] == "running"
    assert state["total_tasks"] == 1
    assert state["completed_tasks"] == []

    loaded = manager.load_state("wf1")
    assert loaded["workflow_id"] == "wf1"


def test_state_manager_update_task_result(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    manager.create_state("wf2", [MINIMAL_TASK])
    manager.update_task_result("wf2", "1.1.1", {"success": True})

    state = manager.load_state("wf2")
    assert "1.1.1" in state["completed_tasks"]
    assert state["results"]["1.1.1"]["result"] == {"success": True}


def test_state_manager_record_failure(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    manager.create_state("wf3", [MINIMAL_TASK])
    manager.record_failure("wf3", "1.1.1", "Something broke")

    state = manager.load_state("wf3")
    assert len(state["failed_tasks"]) == 1
    assert state["failed_tasks"][0]["task_id"] == "1.1.1"
    assert "Something broke" in state["failed_tasks"][0]["error"]


def test_state_manager_finalize(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    manager.create_state("wf4", [MINIMAL_TASK])
    manager.finalize("wf4")

    state = manager.load_state("wf4")
    assert state["status"] == "completed"
    assert "completed_at" in state


def test_state_manager_list_workflows(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    manager.create_state("wf_a", [MINIMAL_TASK])
    manager.create_state("wf_b", [MINIMAL_TASK, MINIMAL_TASK])

    summaries = manager.list_workflows()
    ids = {s["workflow_id"] for s in summaries}
    assert "wf_a" in ids
    assert "wf_b" in ids


def test_state_manager_load_missing_returns_empty(tmp_path: Path) -> None:
    manager = WorkflowStateManager(tmp_path / "workflows")
    result = manager.load_state("nonexistent")
    assert result == {}


# ---------------------------------------------------------------------------
# BasicWorkflowExecutor tests
# ---------------------------------------------------------------------------


def _make_executor(tmp_path: Path, registry: MagicMock) -> BasicWorkflowExecutor:
    executor = BasicWorkflowExecutor(
        registry=registry,
        state_dir=tmp_path / "workflows",
    )
    return executor


def test_execute_workflow_success(tmp_path: Path) -> None:
    registry = MagicMock()
    registry.call_tool.return_value = {"success": True, "text": "ok"}

    plan_dir = _make_plan_dir(tmp_path)
    executor = _make_executor(tmp_path, registry)

    result = executor.execute_workflow("test_wf", plan_dir)

    assert result["workflow_id"] == "test_wf"
    assert result["completed"] == 1
    assert result["failed"] == 0
    assert "1.1.1" in result["results"]


def test_execute_workflow_missing_atomictasks(tmp_path: Path) -> None:
    registry = MagicMock()
    executor = _make_executor(tmp_path, registry)

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        executor.execute_workflow("test_wf", empty_dir)


def test_execute_workflow_task_failure_continue(tmp_path: Path) -> None:
    """Tasks with failure_mode != 'fail-fast' should not stop the workflow."""
    task_a = {**MINIMAL_TASK, "task_id": "1.1.1", "failure_mode": "ask-user"}
    task_b = {**MINIMAL_TASK, "task_id": "1.1.2", "failure_mode": "ask-user"}
    plan_dir = _make_plan_dir(tmp_path, [task_a, task_b])

    registry = MagicMock()
    registry.call_tool.side_effect = [RuntimeError("Task A failed"), {"success": True}]

    executor = _make_executor(tmp_path, registry)
    result = executor.execute_workflow("test_wf", plan_dir)

    assert result["failed"] == 1
    assert result["completed"] == 1


def test_execute_workflow_fail_fast(tmp_path: Path) -> None:
    """fail-fast tasks should halt execution on first error."""
    task_a = {**MINIMAL_TASK, "task_id": "1.1.1", "failure_mode": "fail-fast"}
    task_b = {**MINIMAL_TASK, "task_id": "1.1.2", "failure_mode": "ask-user"}
    plan_dir = _make_plan_dir(tmp_path, [task_a, task_b])

    registry = MagicMock()
    registry.call_tool.side_effect = RuntimeError("Hard failure")

    executor = _make_executor(tmp_path, registry)
    result = executor.execute_workflow("test_wf", plan_dir)

    # Only task_a should have been attempted; task_b skipped
    assert result["failed"] == 1
    assert result["completed"] == 0
    assert registry.call_tool.call_count == 1


def test_map_task_to_tool_search(tmp_path: Path) -> None:
    registry = MagicMock()
    executor = _make_executor(tmp_path, registry)

    task = {**MINIMAL_TASK, "action": "search for competitors", "tool_or_endpoint": "search"}
    assert executor._map_task_to_tool(task) == "search"


def test_map_task_to_tool_read_file(tmp_path: Path) -> None:
    registry = MagicMock()
    executor = _make_executor(tmp_path, registry)

    task = {**MINIMAL_TASK, "action": "Read the config file", "tool_or_endpoint": "file read"}
    assert executor._map_task_to_tool(task) == "read_file"


def test_map_task_to_tool_default_bash(tmp_path: Path) -> None:
    registry = MagicMock()
    executor = _make_executor(tmp_path, registry)

    task = {**MINIMAL_TASK, "action": "Do something unusual", "tool_or_endpoint": "custom"}
    assert executor._map_task_to_tool(task) == "bash_execute"


def test_execution_order_by_depth(tmp_path: Path) -> None:
    registry = MagicMock()
    registry.call_tool.return_value = {"success": True}
    executor = _make_executor(tmp_path, registry)

    deep_task = {**MINIMAL_TASK, "task_id": "2.1.1", "depth": 3}
    shallow_task = {**MINIMAL_TASK, "task_id": "1.1", "depth": 1}
    plan_dir = _make_plan_dir(tmp_path, [deep_task, shallow_task])

    result = executor.execute_workflow("order_test", plan_dir)

    # Both should complete; order is shallow-first
    assert result["completed"] == 2
    calls = registry.call_tool.call_args_list
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_workflow_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import cli
    import cli_workflow

    plan_dir = _make_plan_dir(tmp_path)

    mock_registry = MagicMock()
    mock_registry.call_tool.return_value = {"success": True}

    monkeypatch.setattr(
        "mcp_server.workflow_executor.ProjectToolRegistry",
        lambda *a, **kw: mock_registry,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "workflow", "execute", str(plan_dir), "--state-dir", str(tmp_path / "wf")],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "workflow_id" in captured.out


def test_cli_workflow_list_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import cli

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "workflow", "list", "--state-dir", str(tmp_path / "wf")],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "No workflows found" in captured.out


def test_cli_workflow_status_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import cli

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "workflow", "status", "missing_id", "--state-dir", str(tmp_path / "wf")],
    )

    exit_code = cli.main()
    assert exit_code == 1
