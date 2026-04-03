"""Agent Spawner module for Agentic OS.

Provides adapters and tools for spawning and managing external agent sessions
(OpenCode, Claude Code) and in-process LangChain subagents.
"""

from .claude_code_adapter import ClaudeCodeAdapter
from .langchain_adapter import LangChainSubagentAdapter
from .opencode_adapter import OpenCodeAdapter
from .tools import (
    get_team_status,
    send_message_to_agent,
    shutdown_team,
    spawn_agent,
    spawn_agent_team,
    wait_for_team,
)

__all__ = [
    # Adapters
    "OpenCodeAdapter",
    "ClaudeCodeAdapter",
    "LangChainSubagentAdapter",
    # Tools
    "spawn_agent",
    "spawn_agent_team",
    "get_team_status",
    "send_message_to_agent",
    "wait_for_team",
    "shutdown_team",
]
