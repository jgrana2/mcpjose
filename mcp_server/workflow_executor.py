"""Basic workflow executor for AtomicTasks.json plans.

Executes workflows defined by the existing decomposition framework
(userapp/DECOMPOSITION.md) using the ProjectToolRegistry.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.workflow_interfaces import WorkflowExecutor
from core.workflow_state import WorkflowStateManager
from langchain_agent.tool_registry import ProjectToolRegistry


_ACTION_TO_TOOL: Dict[str, str] = {
    "search": "search",
    "navigate": "navigate_to_url",
    "browse": "navigate_to_url",
    "read": "read_file",
    "file": "read_file",
    "write": "write_file",
    "save": "write_file",
    "whatsapp": "send_ws_msg",
    "message": "send_ws_msg",
    "send": "send_ws_msg",
    "llm": "call_llm",
    "call": "call_llm",
    "generate": "generate_image",
    "image": "generate_image",
    "ocr": "google_ocr",
    "transcribe": "transcribe_audio",
    "vision": "gemini_vision_tool",
    "list": "list_directory",
    "directory": "list_directory",
    "bash": "bash_execute",
    "run": "bash_execute",
    "execute": "bash_execute",
}


class BasicWorkflowExecutor(WorkflowExecutor):
    def __init__(
        self,
        registry: Optional[ProjectToolRegistry] = None,
        state_dir: Path = Path("workflows"),
    ) -> None:
        self.registry = registry or ProjectToolRegistry()
        self.state_manager = WorkflowStateManager(state_dir)

    @property
    def name(self) -> str:
        return "basic_workflow_executor"

    def execute_workflow(self, workflow_id: str, plan_dir: Path) -> Dict[str, Any]:
        atomic_tasks = self._load_atomic_tasks(plan_dir / "AtomicTasks.json")
        task_tree = self._load_task_tree(plan_dir / "TaskTree.json")

        self.state_manager.create_state(workflow_id, atomic_tasks)
        results: Dict[str, Any] = {}
        ordered_tasks = self._get_execution_order(atomic_tasks, task_tree)

        for task in ordered_tasks:
            task_id = task["task_id"]
            self.state_manager.set_current_task(workflow_id, task_id)
            try:
                result = self._execute_with_retry(task)
                results[task_id] = result
                self.state_manager.update_task_result(workflow_id, task_id, result)
            except Exception as exc:
                self.state_manager.record_failure(workflow_id, task_id, str(exc))
                if task.get("failure_mode") == "fail-fast":
                    break

        self.state_manager.finalize(workflow_id)
        final_state = self.state_manager.load_state(workflow_id)
        return {
            "workflow_id": workflow_id,
            "completed": len(final_state.get("completed_tasks", [])),
            "failed": len(final_state.get("failed_tasks", [])),
            "results": results,
        }

    def _execute_with_retry(self, task: Dict[str, Any]) -> Any:
        retry_policy = task.get("retry_policy", {})
        max_attempts = retry_policy.get("max_attempts", 1)
        backoff_seconds: List[float] = retry_policy.get("backoff_seconds", [])

        last_exc: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                return self._execute_single_task(task)
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    delay = backoff_seconds[attempt] if attempt < len(backoff_seconds) else 1.0
                    time.sleep(delay)

        raise last_exc  # type: ignore[misc]

    def _execute_single_task(self, task: Dict[str, Any]) -> Any:
        tool_name = self._map_task_to_tool(task)
        arguments = self._prepare_arguments(task)
        return self.registry.call_tool(tool_name, arguments)

    def _map_task_to_tool(self, task: Dict[str, Any]) -> str:
        tool_hint = task.get("tool_or_endpoint", "").lower()
        for keyword, tool in _ACTION_TO_TOOL.items():
            if keyword in tool_hint:
                return tool

        action = task.get("action", "").lower()
        for keyword, tool in _ACTION_TO_TOOL.items():
            if keyword in action:
                return tool

        return "bash_execute"

    def _prepare_arguments(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self._map_task_to_tool(task)
        action = task.get("action", "")
        exact_inputs = task.get("exact_inputs", [])

        file_paths = [
            inp.replace("path:", "").strip()
            for inp in exact_inputs
            if inp.startswith("path:")
        ]

        if tool_name == "read_file" and file_paths:
            return {"path": file_paths[0]}
        if tool_name == "bash_execute":
            return {"command": action}
        if tool_name in {"call_llm"}:
            return {"prompt": action}
        if tool_name == "search":
            return {"query": action}
        if tool_name == "navigate_to_url" and file_paths:
            return {"url": file_paths[0]}

        return {"command": action}

    def _load_atomic_tasks(self, path: Path) -> List[Dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("atomic_tasks", data if isinstance(data, list) else [])

    def _load_task_tree(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _get_execution_order(
        self,
        atomic_tasks: List[Dict[str, Any]],
        task_tree: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return sorted(
            atomic_tasks,
            key=lambda t: (t.get("depth", 0), t.get("task_id", "")),
        )
