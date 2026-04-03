"""Agent Adapter Interface for Agentic OS.

Provides a unified interface for different agent types (OpenCode, Claude Code,
LangChain subagents) to be orchestrated by the Agent Team Coordinator.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class AgentStatus(Enum):
    """Status of an agent in the team."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"  # Waiting for next task
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class AgentType(Enum):
    """Types of agents that can be orchestrated."""

    OPENCODE = "opencode"
    CLAUDE_CODE = "claude_code"
    LANGCHAIN_SUBAGENT = "langchain_subagent"


@dataclass
class AgentInstance:
    """Represents a running agent instance."""

    agent_id: str
    agent_type: AgentType
    role: str  # e.g., "business_analyst", "tech_lead", "qa_engineer"
    pid: Optional[int]
    work_dir: Path
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "role": self.role,
            "pid": self.pid,
            "work_dir": str(self.work_dir),
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInstance":
        return cls(
            agent_id=data["agent_id"],
            agent_type=AgentType(data["agent_type"]),
            role=data["role"],
            pid=data.get("pid"),
            work_dir=Path(data["work_dir"]),
            status=AgentStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            exit_code=data.get("exit_code"),
            error_message=data.get("error_message"),
        )


class AgentAdapter(ABC):
    """Abstract base class for agent adapters.

        Each agent type (OpenCode, Claude Code, LangChain) implements this interface
    to provide a unified way to spawn, monitor, and communicate with agents.
    """

    @abstractmethod
    def spawn(
        self,
        agent_id: str,
        role: str,
        task: Dict[str, Any],
        work_dir: Path,
        **kwargs: Any,
    ) -> AgentInstance:
        """Spawn a new agent instance.

        Args:
            agent_id: Unique identifier for this agent.
            role: The role this agent plays (e.g., "business_analyst").
            task: The atomic task from AtomicTasks.json.
            work_dir: Directory for agent outputs and communication.
            **kwargs: Additional agent-specific options.

        Returns:
            AgentInstance representing the spawned agent.
        """
        pass

    @abstractmethod
    def check_status(self, agent: AgentInstance) -> AgentStatus:
        """Check the current status of an agent.

        Args:
            agent: The agent instance to check.

        Returns:
            Current status of the agent.
        """
        pass

    @abstractmethod
    def send_message(self, agent: AgentInstance, message: Dict[str, Any]) -> bool:
        """Send a message to an agent.

        Messages are written to the shared JSON state.

        Args:
            agent: The target agent.
            message: Message dictionary with 'type', 'content', etc.

        Returns:
            True if message was queued successfully.
        """
        pass

    @abstractmethod
    def read_messages(self, agent: AgentInstance) -> list[Dict[str, Any]]:
        """Read messages sent to an agent.

        Args:
            agent: The agent to read messages for.

        Returns:
            List of messages for this agent.
        """
        pass

    @abstractmethod
    def get_output(self, agent: AgentInstance) -> Dict[str, Any]:
        """Get the output/artifacts produced by an agent.

        Args:
            agent: The agent to get output from.

        Returns:
            Dictionary with 'artifacts', 'logs', 'result', etc.
        """
        pass

    @abstractmethod
    def shutdown(self, agent: AgentInstance, graceful: bool = True) -> bool:
        """Shutdown an agent.

        Args:
            agent: The agent to shutdown.
            graceful: If True, send shutdown signal and wait. If False, kill immediately.

        Returns:
            True if shutdown was successful.
        """
        pass

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the type of agent this adapter handles."""
        pass
