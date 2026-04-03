"""Workflow orchestration interfaces.

Extends the core/interfaces.py pattern with workflow-specific abstractions.
Implements SOLID principles:
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depend on abstractions, not concretions
- Open/Closed: Extend via new executors without modifying existing code
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class WorkflowExecutor(ABC):
    """Abstract base class for workflow execution."""

    @abstractmethod
    def execute_workflow(self, workflow_id: str, plan_dir: Path) -> Dict[str, Any]:
        """Execute a workflow from a plan directory containing AtomicTasks.json.

        Args:
            workflow_id: Unique identifier for this workflow run.
            plan_dir: Directory containing AtomicTasks.json and TaskTree.json.

        Returns:
            Dictionary with workflow_id, completed count, failed count, and results.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return executor name."""
        pass


class TaskExecutor(ABC):
    """Abstract base class for individual atomic task execution."""

    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single atomic task.

        Args:
            task: Atomic task dictionary from AtomicTasks.json.

        Returns:
            Dictionary with execution result.
        """
        pass

    @property
    @abstractmethod
    def supported_actions(self) -> List[str]:
        """Return list of action keywords this executor handles."""
        pass
