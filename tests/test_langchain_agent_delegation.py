from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.tool_registry import ProjectToolRegistry


def test_delegate_to_agent_unknown_agent_returns_error(tmp_path: Path) -> None:
    registry = ProjectToolRegistry()

    result = registry.delegate_to_agent(
        agent_name="nope",
        workflow_id="wf1",
        plan_dir=str(tmp_path),
        state_dir=str(tmp_path),
    )

    assert "error" in result
    assert result["available_agents"] == ["basic_workflow_executor"]


def test_delegate_to_agent_routes_to_basic_workflow_executor(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeExecutor:
        def __init__(self, registry: object, state_dir: Path) -> None:
            captured["registry"] = registry
            captured["state_dir"] = state_dir

        def execute_workflow(
            self, workflow_id: str, plan_dir: Path
        ) -> dict[str, object]:
            captured["workflow_id"] = workflow_id
            captured["plan_dir"] = plan_dir
            return {"ok": True, "workflow_id": workflow_id}

    fake_module = types.ModuleType("mcp_server.workflow_executor")
    fake_module.BasicWorkflowExecutor = FakeExecutor
    # Save original module and clean up after test
    original_module = sys.modules.get("mcp_server.workflow_executor")
    sys.modules["mcp_server.workflow_executor"] = fake_module

    try:
        registry = ProjectToolRegistry()
        plan_dir = tmp_path / "plan"
        state_dir = tmp_path / "state"

        result = registry.delegate_to_agent(
            agent_name="basic_workflow_executor",
            workflow_id="wf1",
            plan_dir=str(plan_dir),
            state_dir=str(state_dir),
        )

        assert result == {"ok": True, "workflow_id": "wf1"}
        assert captured["registry"] is registry
        assert captured["state_dir"] == state_dir
        assert captured["workflow_id"] == "wf1"
        assert captured["plan_dir"] == plan_dir
    finally:
        # Restore original module to prevent test pollution
        if original_module is None:
            sys.modules.pop("mcp_server.workflow_executor", None)
        else:
            sys.modules["mcp_server.workflow_executor"] = original_module
