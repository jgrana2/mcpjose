"""Workflow state management.

Uses JSON files following existing patterns in userapp/outputs/.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class WorkflowStateManager:
    """Manage workflow state using JSON files."""

    def __init__(self, state_dir: Path = Path("workflows")) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True)

    def create_state(self, workflow_id: str, atomic_tasks: List[Dict]) -> Dict[str, Any]:
        """Create initial workflow state and persist it.

        Args:
            workflow_id: Unique workflow identifier.
            atomic_tasks: List of atomic task dictionaries.

        Returns:
            Initial state dictionary.
        """
        state: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
            "status": "running",
            "total_tasks": len(atomic_tasks),
            "completed_tasks": [],
            "failed_tasks": [],
            "current_task": None,
            "results": {},
            "metadata": {
                "executor": "basic_workflow_executor",
                "version": "1.0",
            },
        }
        self._save_state(workflow_id, state)
        return state

    def update_task_result(
        self, workflow_id: str, task_id: str, result: Dict[str, Any]
    ) -> None:
        """Record a completed task result.

        Args:
            workflow_id: Workflow identifier.
            task_id: Task identifier from AtomicTasks.json.
            result: Tool execution result.
        """
        state = self.load_state(workflow_id)
        state["results"][task_id] = {
            "result": result,
            "completed_at": datetime.now().isoformat(),
        }
        if task_id not in state["completed_tasks"]:
            state["completed_tasks"].append(task_id)
        state["current_task"] = None
        self._save_state(workflow_id, state)

    def record_failure(
        self, workflow_id: str, task_id: str, error: str
    ) -> None:
        """Record a failed task.

        Args:
            workflow_id: Workflow identifier.
            task_id: Task identifier.
            error: Error message.
        """
        state = self.load_state(workflow_id)
        state["failed_tasks"].append(
            {
                "task_id": task_id,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
        state["current_task"] = None
        self._save_state(workflow_id, state)

    def set_current_task(self, workflow_id: str, task_id: str) -> None:
        """Mark the currently executing task.

        Args:
            workflow_id: Workflow identifier.
            task_id: Task identifier.
        """
        state = self.load_state(workflow_id)
        state["current_task"] = task_id
        self._save_state(workflow_id, state)

    def finalize(self, workflow_id: str) -> None:
        """Mark workflow as completed.

        Args:
            workflow_id: Workflow identifier.
        """
        state = self.load_state(workflow_id)
        state["status"] = "completed"
        state["completed_at"] = datetime.now().isoformat()
        self._save_state(workflow_id, state)

    def load_state(self, workflow_id: str) -> Dict[str, Any]:
        """Load workflow state from disk.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            State dictionary, or empty dict if not found.
        """
        state_file = self._state_file(workflow_id)
        if state_file.exists():
            return json.loads(state_file.read_text(encoding="utf-8"))
        return {}

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflow states.

        Returns:
            List of summary dictionaries for each workflow.
        """
        summaries = []
        for state_dir in sorted(self.state_dir.iterdir()):
            state_file = state_dir / "state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                summaries.append(
                    {
                        "workflow_id": state.get("workflow_id"),
                        "status": state.get("status"),
                        "created_at": state.get("created_at"),
                        "total_tasks": state.get("total_tasks", 0),
                        "completed": len(state.get("completed_tasks", [])),
                        "failed": len(state.get("failed_tasks", [])),
                    }
                )
        return summaries

    def _state_file(self, workflow_id: str) -> Path:
        workflow_dir = self.state_dir / workflow_id
        workflow_dir.mkdir(exist_ok=True)
        return workflow_dir / "state.json"

    def _save_state(self, workflow_id: str, state: Dict[str, Any]) -> None:
        self._state_file(workflow_id).write_text(
            json.dumps(state, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
