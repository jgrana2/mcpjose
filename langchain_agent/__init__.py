"""LangChain agent package for MCP Jose."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .agent import MCPJoseLangChainAgent
    from .context import ProjectContextLoader, SkillDocument
    from .tool_registry import ProjectToolRegistry

__all__ = [
    "MCPJoseLangChainAgent",
    "ProjectContextLoader",
    "ProjectToolRegistry",
    "SkillDocument",
]


def __getattr__(name: str) -> Any:
    if name == "MCPJoseLangChainAgent":
        from .agent import MCPJoseLangChainAgent as value

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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
