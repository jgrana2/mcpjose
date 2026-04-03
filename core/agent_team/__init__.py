"""Agent Team module for Agentic OS.

This module provides the infrastructure for orchestrating cross-functional
agent teams using shared JSON files for coordination.
"""

from .adapter import AgentAdapter, AgentInstance, AgentStatus, AgentType
from .coordinator import AgentTeamCoordinator
from .state import MessageBus, Task, TaskBoard, TaskStatus

__all__ = [
    "AgentAdapter",
    "AgentInstance",
    "AgentStatus",
    "AgentType",
    "AgentTeamCoordinator",
    "MessageBus",
    "Task",
    "TaskBoard",
    "TaskStatus",
]
