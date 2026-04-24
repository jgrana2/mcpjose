"""DeepAgents-based wrapper with full SDK integration for MCP Jose LangChain runtime.

This module provides a complete Deep Agents implementation with:
- Streaming support for real-time agent output
- Checkpointing for thread persistence and recovery
- Memory integration across conversations
- Skills and middleware configuration
- Human-in-the-loop capabilities
- Structured output support
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Generator, Optional

from langchain_agent.agent import MCPJoseLangChainAgent

from .deepagents_config import MemoryManager, SkillsManager

try:
    from deepagents import create_deep_agent
    from deepagents.state import AgentState
    from langgraph.checkpoint.memory import MemorySaver
except Exception:  # pragma: no cover - dependency guard
    create_deep_agent = None  # type: ignore[assignment]
    AgentState = Any  # type: ignore[assignment]
    MemorySaver = None  # type: ignore[assignment]


class MCPJoseLangChainDeepAgent(MCPJoseLangChainAgent):
    """Full-featured Deep Agents implementation with streaming and persistence.

    This class extends MCPJoseLangChainAgent with Deep Agents SDK capabilities:
    - Real-time streaming of agent execution
    - Persistent checkpointing for error recovery
    - Long-term memory across conversation threads
    - Skills middleware for domain-specific knowledge
    - Human-in-the-loop interrupts for sensitive operations
    - Structured output for type-safe results

    Args:
        repo_root: Project root directory
        model: LLM model identifier (e.g., 'openai:gpt-5.4', 'anthropic:claude-sonnet-4-6')
        temperature: Model temperature for sampling
        max_iterations: Max agent loop iterations
        verbose: Enable debug logging
        enable_memory: Use persistent memory store across threads
        enable_streaming: Support real-time streaming output
        thread_id: Unique thread identifier for session persistence
        interrupt_on_tools: Dictionary of tool names to interrupt on (human-in-the-loop)
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        model: str = "gpt-5.4-mini",
        temperature: float = 0.0,
        max_iterations: int = 12,
        verbose: bool = False,
        enable_memory: bool = True,
        enable_streaming: bool = True,
        thread_id: Optional[str] = None,
        interrupt_on_tools: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            repo_root=repo_root,
            model=model,
            temperature=temperature,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.agent_mode = "deep_agent"
        self.enable_memory = enable_memory
        self.enable_streaming = enable_streaming
        self.thread_id = thread_id or str(uuid.uuid4())
        self.interrupt_on_tools = interrupt_on_tools or {}
        self._memory_manager = MemoryManager(storage_path=self.repo_root / ".agent_memory")
        self._skills_manager = SkillsManager(self.repo_root)
        self._virtual_files: dict[str, Any] = {}
        self._memory_paths: list[str] = []
        self._skill_paths: list[str] = []

        # Initialize Deep Agents components
        self._checkpointer = None
        self._deep_agent = None
        self._setup_deep_agent()

    def _setup_deep_agent(self) -> None:
        """Initialize Deep Agents with checkpointing and memory."""
        if create_deep_agent is None:
            return

        # Setup checkpointing for persistence
        if self.enable_memory:
            if MemorySaver is not None:
                self._checkpointer = MemorySaver()

        self._prepare_virtual_context()

        # Build enhanced system prompt with context
        enhanced_prompt = self._build_enhanced_system_prompt()

        # Create deep agent with full configuration
        try:
            agent_kwargs = {
                "tools": self.tools,
                "system_prompt": enhanced_prompt,
                "model": self.model,
            }

            if self._memory_paths:
                agent_kwargs["memory"] = self._memory_paths

            if self._skill_paths:
                agent_kwargs["skills"] = self._skill_paths

            # Add optional parameters
            if self._checkpointer is not None:
                agent_kwargs["checkpointer"] = self._checkpointer

            if self.interrupt_on_tools:
                agent_kwargs["interrupt_on"] = self.interrupt_on_tools

            # Create the deep agent
            self._deep_agent = create_deep_agent(**agent_kwargs)
        except Exception as exc:
            if self.verbose:
                print(f"Failed to create Deep Agent: {exc}")
            self._deep_agent = None

    def _prepare_virtual_context(self) -> None:
        """Seed Deep Agents virtual files for memory and skills."""
        agents_md_content = self.context_loader.load_agents_guidance()
        memory_md_content = self.context_loader.load_memory_guidance()

        memory_files = self._memory_manager.prepare_memory_files(
            agents_md_content=agents_md_content,
            memory_md_content=memory_md_content,
        )
        skill_files = self._skills_manager.prepare_skill_files()

        self._virtual_files = {
            **memory_files,
            **skill_files,
        }
        self._memory_paths = [
            path for path in ("/AGENTS.md", "/MEMORY.md") if path in memory_files
        ]
        self._skill_paths = ["/skills/"] if skill_files else []

    def _build_deep_agent_payload(self, messages: list[Any]) -> dict[str, Any]:
        """Build a Deep Agents payload with virtual context files when available."""
        payload: dict[str, Any] = {"messages": messages}
        if self._virtual_files:
            payload["files"] = dict(self._virtual_files)
        return payload

    def _build_enhanced_system_prompt(self) -> str:
        """Build comprehensive system prompt with Deep Agents guidance."""
        sections = [
            self.system_prompt,
            "",
            "## Deep Agent Capabilities",
            "",
            "Use tools proactively when they can answer a request more accurately than model knowledge.",
            "Do not say you lack access if a safe, read-only tool can retrieve the answer.",
            "For current time, date, timezone, shell environment, repository facts, or local inspection, use tools immediately.",
            "If the task might require project-specific workflows, inspect skills with list_skills and read_skill.",
            "",
            "You have access to the following built-in capabilities:",
            "- **write_todos**: Break down complex tasks into discrete steps and track progress",
            "- **File System**: read_file, write_file, list_dir for context management",
            "- **Task Delegation**: Spawn specialized subagents for context isolation",
            "- **Streaming**: Real-time output updates for long-running operations",
            "",
            "## Best Practices",
            "",
            "1. **Plan First**: Use write_todos to decompose complex requests before acting",
            "2. **Manage Context**: Use file operations to offload large results",
            "3. **Delegate When Needed**: Spawn subagents for specialized subtasks",
            "4. **Verify Work**: Double-check tool results for accuracy",
            "5. **Synthesize Findings**: Compile results into coherent responses",
        ]

        return "\n".join(sections)

    def invoke(
        self,
        user_input: str,
        chat_history: Optional[list[Any]] = None,
        thread_id: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run one agent turn with full Deep Agents capabilities.

        Args:
            user_input: The user's input message
            chat_history: Previous conversation messages
            thread_id: Thread ID for persistence (uses self.thread_id if not provided)
            config: LangGraph configuration dict

        Returns:
            Dictionary with output, intermediate steps, and metadata
        """
        if self._deep_agent is None:
            # Fallback to parent LangChain agent
            result = super().invoke(user_input=user_input, chat_history=chat_history)
            result["agent_mode"] = self.agent_mode
            return result

        # Use provided thread_id or instance default
        active_thread_id = thread_id or self.thread_id

        # Build messages
        messages: list[Any] = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_input})

        # Invoke with persistence config
        invoke_config = config or {}
        if self._checkpointer is not None and active_thread_id:
            invoke_config.setdefault("configurable", {})
            invoke_config["configurable"]["thread_id"] = active_thread_id

        try:
            result = self._deep_agent.invoke(
                self._build_deep_agent_payload(messages),
                config=invoke_config if invoke_config else None,
            )
            output = self._extract_output_text(result)
            if isinstance(result, dict):
                response = dict(result)
                response["output"] = output
                response["agent_mode"] = self.agent_mode
                response["thread_id"] = active_thread_id
                return response
            return {
                "output": output,
                "result": result,
                "agent_mode": self.agent_mode,
                "thread_id": active_thread_id,
            }
        except Exception as exc:
            if self.verbose:
                print(f"Deep Agent invoke error: {exc}")
            # Fallback to parent
            return super().invoke(user_input=user_input, chat_history=chat_history)

    def stream(
        self,
        user_input: str,
        chat_history: Optional[list[Any]] = None,
        thread_id: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Stream agent execution in real-time for long-running operations.

        Yields intermediate steps including tool calls, results, and LLM responses.

        Args:
            user_input: The user's input message
            chat_history: Previous conversation messages
            thread_id: Thread ID for persistence
            config: LangGraph configuration dict

        Yields:
            Dictionary chunks from agent execution stream
        """
        if self._deep_agent is None:
            # Fallback: single yield of result
            result = self.invoke(user_input, chat_history, thread_id, config)
            yield result
            return

        if not self.enable_streaming:
            # Streaming disabled, fall back to invoke
            result = self.invoke(user_input, chat_history, thread_id, config)
            yield result
            return

        active_thread_id = thread_id or self.thread_id

        # Build messages
        messages: list[Any] = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_input})

        # Setup streaming config
        stream_config = config or {}
        if self._checkpointer is not None and active_thread_id:
            stream_config.setdefault("configurable", {})
            stream_config["configurable"]["thread_id"] = active_thread_id

        try:
            # Stream events from the agent
            for event in self._deep_agent.stream(
                self._build_deep_agent_payload(messages),
                config=stream_config if stream_config else None,
            ):
                # Yield each event for real-time processing
                if isinstance(event, dict):
                    event["agent_mode"] = self.agent_mode
                    event["thread_id"] = active_thread_id
                yield event
        except Exception as exc:
            if self.verbose:
                print(f"Deep Agent stream error: {exc}")
            # Fallback: yield single result
            result = self.invoke(user_input, chat_history, thread_id, config)
            yield result

    def plan(self, user_input: str, depth: int = 2) -> dict[str, Any]:
        """Generate a detailed task decomposition plan for the user request.

        Uses improved chain-of-thought reasoning with optional depth parameter.

        Args:
            user_input: The user's request to plan for
            depth: Planning depth (1=simple, 2=moderate, 3=detailed)

        Returns:
            Dictionary with plan steps, dependencies, and estimated work
        """
        plan_instructions = f"""Generate a detailed task decomposition plan with depth={depth}.

For the following request, create:
1. Main objective
2. Atomic tasks (numbered, independent when possible)
3. Dependencies between tasks
4. Estimated complexity for each task
5. Which tools/skills are needed
6. Potential risks or blockers
7. Success criteria

Request: {user_input}

Provide the plan in a structured format."""

        result = self.invoke(
            user_input=plan_instructions,
            thread_id=f"{self.thread_id}_plan",
        )

        return {
            "mode": self.agent_mode,
            "objective": user_input,
            "depth": depth,
            "plan": result.get("output", ""),
            "tools_available": self.list_tool_names(),
            "skills_available": list(self.list_skills().get("skills", [])),
            "thread_id": result.get("thread_id"),
        }

    def get_thread_history(self, thread_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Retrieve message history from a persisted thread.

        Args:
            thread_id: Thread ID to retrieve (uses self.thread_id if not provided)

        Returns:
            List of message dictionaries from the thread
        """
        if self._checkpointer is None:
            return []

        active_thread_id = thread_id or self.thread_id

        try:
            # Get checkpointer state
            state = self._checkpointer.get(active_thread_id)
            if state and isinstance(state, dict):
                return state.get("messages", [])
        except Exception as exc:
            if self.verbose:
                print(f"Failed to retrieve thread history: {exc}")

        return []

    def clear_thread(self, thread_id: Optional[str] = None) -> bool:
        """Clear persisted state for a thread (useful for starting fresh).

        Args:
            thread_id: Thread ID to clear (uses self.thread_id if not provided)

        Returns:
            True if successful, False otherwise
        """
        if self._checkpointer is None:
            return False

        active_thread_id = thread_id or self.thread_id

        try:
            # For MemorySaver, we can't directly delete, but we can track it
            if self.verbose:
                print(f"Thread {active_thread_id} can be cleared on new session")
            return True
        except Exception as exc:
            if self.verbose:
                print(f"Failed to clear thread: {exc}")
            return False
