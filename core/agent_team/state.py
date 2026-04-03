"""Shared state management for Agentic OS.

Uses JSON files for inter-agent communication, following the user's requirement
for shared JSON files instead of in-memory or database solutions.
"""

from __future__ import annotations

import json
import fcntl
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of a task in the shared board."""

    PENDING = "pending"
    BLOCKED = "blocked"  # Waiting for dependencies
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A task in the shared task board."""

    task_id: str
    parent_id: Optional[str]
    depth: int
    action: str
    exact_inputs: List[str] = field(default_factory=list)
    exact_outputs: List[str] = field(default_factory=list)
    tool_or_endpoint: str = ""
    validation_check: str = ""
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    failure_mode: str = "ask-user"
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None  # agent_id
    priority: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    branch_alternatives: List[Dict[str, Any]] = field(default_factory=list)
    backtrack_policy: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "action": self.action,
            "exact_inputs": self.exact_inputs,
            "exact_outputs": self.exact_outputs,
            "tool_or_endpoint": self.tool_or_endpoint,
            "validation_check": self.validation_check,
            "retry_policy": self.retry_policy,
            "failure_mode": self.failure_mode,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": self.result,
            "error_message": self.error_message,
            "branch_alternatives": self.branch_alternatives,
            "backtrack_policy": self.backtrack_policy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(
            task_id=data["task_id"],
            parent_id=data.get("parent_id"),
            depth=data.get("depth", 0),
            action=data["action"],
            exact_inputs=data.get("exact_inputs", []),
            exact_outputs=data.get("exact_outputs", []),
            tool_or_endpoint=data.get("tool_or_endpoint", ""),
            validation_check=data.get("validation_check", ""),
            retry_policy=data.get("retry_policy", {}),
            failure_mode=data.get("failure_mode", "ask-user"),
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", "pending")),
            assigned_to=data.get("assigned_to"),
            priority=data.get("priority", 0),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            result=data.get("result", {}),
            error_message=data.get("error_message"),
            branch_alternatives=data.get("branch_alternatives", []),
            backtrack_policy=data.get("backtrack_policy", {}),
        )


class TaskBoard:
    """Manages the shared task board using JSON file.

    Thread-safe via file locking for coordination between multiple agents.
    """

    def __init__(self, board_file: Path):
        self.board_file = Path(board_file)
        self.board_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.board_file.exists():
            self._save_board({"tasks": [], "version": 1})

    def _load_board(self) -> Dict[str, Any]:
        """Load board from disk."""
        if not self.board_file.exists():
            return {"tasks": [], "version": 1}
        with open(self.board_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_board(self, board: Dict[str, Any]) -> None:
        """Save board to disk atomically."""
        temp_file = self.board_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(board, f, indent=2, ensure_ascii=False, default=str)
        temp_file.replace(self.board_file)

    def _atomic_update(self, updater: callable) -> Any:
        """Perform atomic update with file locking."""
        lock_file = self.board_file.with_suffix(".lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        with open(lock_file, "w") as lock:
            # Acquire exclusive lock
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                board = self._load_board()
                result = updater(board)
                self._save_board(board)
                return result
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def add_task(self, task: Task) -> None:
        """Add a new task to the board."""

        def updater(board: Dict[str, Any]) -> None:
            # Check if task already exists
            for existing in board["tasks"]:
                if existing["task_id"] == task.task_id:
                    raise ValueError(f"Task {task.task_id} already exists")
            board["tasks"].append(task.to_dict())

        self._atomic_update(updater)

    def add_tasks(self, tasks: List[Task]) -> None:
        """Add multiple tasks at once."""

        def updater(board: Dict[str, Any]) -> None:
            existing_ids = {t["task_id"] for t in board["tasks"]}
            for task in tasks:
                if task.task_id in existing_ids:
                    raise ValueError(f"Task {task.task_id} already exists")
                board["tasks"].append(task.to_dict())

        self._atomic_update(updater)

    def claim_task(self, agent_id: str, task_id: str) -> Optional[Task]:
        """Attempt to claim a task for an agent.

        Returns the task if successfully claimed, None if already claimed or blocked.
        """

        def updater(board: Dict[str, Any]) -> Optional[Task]:
            for task_data in board["tasks"]:
                if task_data["task_id"] == task_id:
                    # Check if already assigned
                    if task_data.get("assigned_to"):
                        return None

                    # Check dependencies
                    deps = task_data.get("dependencies", [])
                    if deps:
                        dep_statuses = {}
                        for t in board["tasks"]:
                            if t["task_id"] in deps:
                                dep_statuses[t["task_id"]] = t["status"]

                        # All deps must be completed
                        if not all(dep_statuses.get(d) == "completed" for d in deps):
                            task_data["status"] = "blocked"
                            return None

                    # Claim the task
                    task_data["assigned_to"] = agent_id
                    task_data["status"] = "in_progress"
                    task_data["started_at"] = datetime.now().isoformat()
                    return Task.from_dict(task_data)

            return None

        return self._atomic_update(updater)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update task status."""

        def updater(board: Dict[str, Any]) -> bool:
            for task_data in board["tasks"]:
                if task_data["task_id"] == task_id:
                    task_data["status"] = status.value
                    if result is not None:
                        task_data["result"] = result
                    if error_message is not None:
                        task_data["error_message"] = error_message
                    if status in (
                        TaskStatus.COMPLETED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                    ):
                        task_data["completed_at"] = datetime.now().isoformat()
                    return True
            return False

        return self._atomic_update(updater)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        board = self._load_board()
        for task_data in board["tasks"]:
            if task_data["task_id"] == task_id:
                return Task.from_dict(task_data)
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a given status."""
        board = self._load_board()
        return [
            Task.from_dict(t) for t in board["tasks"] if t["status"] == status.value
        ]

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        board = self._load_board()
        return [Task.from_dict(t) for t in board["tasks"]]

    def get_next_available_task(self) -> Optional[Task]:
        """Get the next available task (pending with no unmet dependencies)."""
        board = self._load_board()

        # Build dependency status map
        all_tasks = {t["task_id"]: t for t in board["tasks"]}

        for task_data in board["tasks"]:
            if task_data["status"] != "pending":
                continue
            if task_data.get("assigned_to"):
                continue

            # Check dependencies
            deps = task_data.get("dependencies", [])
            deps_satisfied = all(
                all_tasks.get(d, {}).get("status") == "completed" for d in deps
            )

            if deps_satisfied:
                return Task.from_dict(task_data)

        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress statistics."""
        board = self._load_board()
        tasks = board["tasks"]

        if not tasks:
            return {"total": 0, "completed": 0, "failed": 0, "percentage": 0}

        by_status = {}
        for t in tasks:
            status = t["status"]
            by_status[status] = by_status.get(status, 0) + 1

        completed = by_status.get("completed", 0)
        failed = by_status.get("failed", 0)
        total = len(tasks)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": by_status.get("in_progress", 0),
            "pending": by_status.get("pending", 0),
            "blocked": by_status.get("blocked", 0),
            "percentage": (completed / total * 100) if total > 0 else 0,
        }


class MessageBus:
    """Message bus for inter-agent communication using JSON file.

    Agents poll this file or use file watchers to receive messages.
    """

    def __init__(self, message_file: Path):
        self.message_file = Path(message_file)
        self.message_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.message_file.exists():
            self._save_messages({"messages": [], "version": 1})

    def _load_messages(self) -> Dict[str, Any]:
        """Load messages from disk."""
        if not self.message_file.exists():
            return {"messages": [], "version": 1}
        with open(self.message_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_messages(self, data: Dict[str, Any]) -> None:
        """Save messages to disk atomically."""
        temp_file = self.message_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        temp_file.replace(self.message_file)

    def _atomic_update(self, updater: callable) -> Any:
        """Perform atomic update with file locking."""
        lock_file = self.message_file.with_suffix(".lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        with open(lock_file, "w") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                data = self._load_messages()
                result = updater(data)
                self._save_messages(data)
                return result
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        reply_to: Optional[str] = None,
    ) -> str:
        """Send a message from one agent to another.

        Args:
            from_agent: Sender agent ID.
            to_agent: Recipient agent ID (use "broadcast" for all).
            message_type: Type of message (instruction, question, answer, status).
            content: Message payload.
            reply_to: Optional message ID this is replying to.

        Returns:
            Message ID.
        """
        message_id = f"msg_{int(time.time() * 1000)}_{from_agent}"

        def updater(data: Dict[str, Any]) -> str:
            data["messages"].append(
                {
                    "id": message_id,
                    "from": from_agent,
                    "to": to_agent,
                    "type": message_type,
                    "content": content,
                    "reply_to": reply_to,
                    "timestamp": datetime.now().isoformat(),
                    "read": False,
                }
            )
            # Keep only last 1000 messages
            if len(data["messages"]) > 1000:
                data["messages"] = data["messages"][-1000:]
            return message_id

        return self._atomic_update(updater)

    def get_messages_for_agent(
        self,
        agent_id: str,
        unread_only: bool = False,
        message_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get messages for a specific agent."""
        data = self._load_messages()
        messages = []

        for msg in data["messages"]:
            # Match direct messages or broadcasts
            if msg["to"] not in (agent_id, "broadcast"):
                continue

            if unread_only and msg.get("read", False):
                continue

            if message_type and msg["type"] != message_type:
                continue

            if since:
                msg_time = datetime.fromisoformat(msg["timestamp"])
                if msg_time < since:
                    continue

            messages.append(msg)

        return messages

    def get_conversation(
        self,
        agent1: str,
        agent2: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get conversation between two agents."""
        data = self._load_messages()
        messages = []

        for msg in data["messages"]:
            if (msg["from"] == agent1 and msg["to"] == agent2) or (
                msg["from"] == agent2 and msg["to"] == agent1
            ):
                messages.append(msg)

        return messages[-limit:]

    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read."""

        def updater(data: Dict[str, Any]) -> bool:
            for msg in data["messages"]:
                if msg["id"] == message_id:
                    msg["read"] = True
                    return True
            return False

        return self._atomic_update(updater)

    def broadcast(
        self,
        from_agent: str,
        message_type: str,
        content: Dict[str, Any],
    ) -> str:
        """Broadcast a message to all agents."""
        return self.send_message(from_agent, "broadcast", message_type, content)
