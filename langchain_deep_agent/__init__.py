"""LangChain Deep Agents package for MCP Jose.

Complete Deep Agents SDK integration with:
- Streaming execution & real-time output
- Persistent memory & checkpointing
- Skills management & middleware
- Human-in-the-loop approvals
- Interactive sessions
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .agent import MCPJoseLangChainDeepAgent
    from .context import ProjectContextLoader, SkillDocument
    from .tool_registry import ProjectToolRegistry
    from .streaming_runner import StreamingRunner, InteractiveStreamingSession
    from .deepagents_config import MemoryManager, SkillsManager, MiddlewareConfig
    from .human_in_loop import HumanInTheLoopConfig, OperationApprovalTracker

__all__ = [
    # Core agent
    "MCPJoseLangChainDeepAgent",
    # Context & tools
    "ProjectContextLoader",
    "ProjectToolRegistry",
    "SkillDocument",
    # Streaming
    "StreamingRunner",
    "InteractiveStreamingSession",
    # Configuration
    "MemoryManager",
    "SkillsManager",
    "MiddlewareConfig",
    # Human-in-the-loop
    "HumanInTheLoopConfig",
    "OperationApprovalTracker",
]


def __getattr__(name: str) -> Any:
    if name == "MCPJoseLangChainDeepAgent":
        from .agent import MCPJoseLangChainDeepAgent as value

        return value
    if name in {"ProjectContextLoader", "SkillDocument"}:
        from .context import ProjectContextLoader, SkillDocument

        return {
            "ProjectContextLoader": ProjectContextLoader,
            "SkillDocument": SkillDocument,
        }[name]
    if name == "ProjectToolRegistry":
        from .tool_registry import ProjectToolRegistry as value

        return value
    if name in {"StreamingRunner", "InteractiveStreamingSession"}:
        from .streaming_runner import StreamingRunner, InteractiveStreamingSession

        return {
            "StreamingRunner": StreamingRunner,
            "InteractiveStreamingSession": InteractiveStreamingSession,
        }[name]
    if name in {"MemoryManager", "SkillsManager", "MiddlewareConfig"}:
        from .deepagents_config import MemoryManager, SkillsManager, MiddlewareConfig

        return {
            "MemoryManager": MemoryManager,
            "SkillsManager": SkillsManager,
            "MiddlewareConfig": MiddlewareConfig,
        }[name]
    if name in {"HumanInTheLoopConfig", "OperationApprovalTracker"}:
        from .human_in_loop import HumanInTheLoopConfig, OperationApprovalTracker

        return {
            "HumanInTheLoopConfig": HumanInTheLoopConfig,
            "OperationApprovalTracker": OperationApprovalTracker,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
