"""Streaming execution runner for Deep Agents with real-time output handling.

This module provides streaming capabilities for Deep Agents execution, enabling
real-time monitoring of agent operation including tool calls, results, and
intermediate thinking steps.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from . import terminal_output
from .agent import MCPJoseLangChainDeepAgent


class StreamingRunner:
    """Execute Deep Agent operations with real-time streaming output.

    This runner provides structured streaming of agent execution with
    support for:
    - Real-time tool call visibility
    - Tool result streaming  
    - Intermediate thinking output
    - Error handling and recovery
    - Progress indication for long operations
    """

    def __init__(
        self,
        agent: MCPJoseLangChainDeepAgent,
        show_intermediate: bool = True,
        show_tool_calls: bool = True,
        show_metadata: bool = False,
    ) -> None:
        """Initialize streaming runner.

        Args:
            agent: De Agent instance to stream from
            show_intermediate: Display intermediate thinking steps
            show_tool_calls: Display tool calls and results
            show_metadata: Display event metadata (timestamps, IDs, etc.)
        """
        self.agent = agent
        self.show_intermediate = show_intermediate
        self.show_tool_calls = show_tool_calls
        self.show_metadata = show_metadata

    def run(
        self,
        user_input: str,
        chat_history: Optional[list[Any]] = None,
        thread_id: Optional[str] = None,
        show_final_result: bool = True,
    ) -> dict[str, Any]:
        """Execute agent request with streaming output.

        Args:
            user_input: The user's input prompt
            chat_history: Previous conversation messages
            thread_id: Thread ID for persistence
            show_final_result: Whether to display final result

        Returns:
            Final result dictionary from agent execution
        """
        terminal_output.print_info(f"Starting agent execution: {user_input[:60]}...")

        final_result = None
        event_count = 0

        try:
            # Try to stream if available, otherwise fall back to invoke
            if self.agent.enable_streaming:
                for event in self.agent.stream(
                    user_input=user_input,
                    chat_history=chat_history,
                    thread_id=thread_id,
                ):
                    event_count += 1
                    self._process_streaming_event(event)
                    final_result = event  # Keep last event
            else:
                # Fall back to regular invoke
                final_result = self.agent.invoke(
                    user_input=user_input,
                    chat_history=chat_history,
                    thread_id=thread_id,
                )
                event_count = 1

            if show_final_result and final_result:
                self._display_final_result(final_result)

            return final_result or {"output": "", "status": "completed"}

        except KeyboardInterrupt:
            terminal_output.print_warning("\n⚠️ Execution interrupted by user")
            return {"output": "", "status": "interrupted"}
        except Exception as exc:
            terminal_output.print_error(f"Execution error: {exc}")
            if self.agent.verbose:
                import traceback
                traceback.print_exc()
            return {"output": "", "status": "error", "error": str(exc)}
        finally:
            terminal_output.print_info(
                f"Execution completed ({event_count} events processed)"
            )

    def _process_streaming_event(self, event: dict[str, Any]) -> None:
        """Process and display a single streaming event."""
        if not isinstance(event, dict):
            return

        event_type = self._infer_event_type(event)

        if event_type == "tool_call":
            self._handle_tool_call_event(event)
        elif event_type == "tool_result":
            self._handle_tool_result_event(event)
        elif event_type == "thinking":
            self._handle_thinking_event(event)
        elif event_type == "final":
            self._handle_final_event(event)
        elif event_type == "error":
            self._handle_error_event(event)

    def _infer_event_type(self, event: dict[str, Any]) -> str:
        """Infer the type of event from its structure."""
        if "error" in event:
            return "error"
        if "messages" in event and event.get("messages"):
            last_msg = event["messages"][-1] if event["messages"] else {}
            if isinstance(last_msg, dict):
                if last_msg.get("type") == "tool":
                    return "tool_result"
                if "tool_calls" in last_msg:
                    return "tool_call"
        if "output" in event:
            return "final"
        if "thinking" in event:
            return "thinking"
        return "unknown"

    def _handle_tool_call_event(self, event: dict[str, Any]) -> None:
        """Display tool call event."""
        if not self.show_tool_calls:
            return

        messages = event.get("messages", [])
        if not messages:
            return

        last_msg = messages[-1] if isinstance(messages, list) else messages
        if isinstance(last_msg, dict) and "tool_calls" in last_msg:
            for tool_call in last_msg["tool_calls"]:
                tool_id = tool_call.get("id", "unknown")
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                tool_args = tool_call.get("function", {}).get("arguments", "{}")

                terminal_output.print_info(f"🔧 Calling: {tool_name}")
                if self.show_metadata:
                    terminal_output.print_debug(f"   ID: {tool_id}")
                try:
                    args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                    for key, value in args_dict.items():
                        value_str = str(value)[:100]
                        terminal_output.print_debug(f"   {key}: {value_str}")
                except (json.JSONDecodeError, TypeError):
                    terminal_output.print_debug(f"   args: {tool_args}")

    def _handle_tool_result_event(self, event: dict[str, Any]) -> None:
        """Display tool result event."""
        if not self.show_tool_calls:
            return

        messages = event.get("messages", [])
        if not messages:
            return

        last_msg = messages[-1] if isinstance(messages, list) else messages
        if isinstance(last_msg, dict) and last_msg.get("type") == "tool":
            result = last_msg.get("content", "")
            result_str = str(result)[:200]  # Truncate long results
            terminal_output.print_success(f"✓ Result: {result_str}")

    def _handle_thinking_event(self, event: dict[str, Any]) -> None:
        """Display agent thinking/reasoning event."""
        if not self.show_intermediate:
            return

        thinking = event.get("thinking", "")
        if thinking:
            thinking_str = str(thinking)[:150]  # Truncate for readability
            terminal_output.print_debug(f"💭 Thinking: {thinking_str}")

    def _handle_final_event(self, event: dict[str, Any]) -> None:
        """Display final output event."""
        output = event.get("output", "")
        if output:
            terminal_output.print_markdown(str(output))

    def _handle_error_event(self, event: dict[str, Any]) -> None:
        """Display error event."""
        error = event.get("error", "Unknown error")
        terminal_output.print_error(f"❌ Error: {error}")

    def _display_final_result(self, result: dict[str, Any]) -> None:
        """Display final execution result."""
        if not isinstance(result, dict):
            return

        output = result.get("output", "")
        status = result.get("status", "completed")
        thread_id = result.get("thread_id", "")

        terminal_output.print_separator()
        terminal_output.print_success(f"✓ Execution {status}")

        if thread_id and self.show_metadata:
            terminal_output.print_info(f"Thread ID: {thread_id}")

        if output:
            terminal_output.print_markdown(str(output))


class InteractiveStreamingSession:
    """Interactive session with persistent Deep Agent connection and streaming.

    Maintains a conversation thread across multiple messages with real-time
    streaming output for each exchange.
    """

    def __init__(
        self,
        agent: MCPJoseLangChainDeepAgent,
        show_intermediate: bool = True,
        show_metadata: bool = False,
    ) -> None:
        """Initialize interactive session.

        Args:
            agent: Deep Agent instance
            show_intermediate: Display intermediate steps
            show_metadata: Display metadata (IDs, timestamps, etc.)
        """
        self.agent = agent
        self.runner = StreamingRunner(
            agent,
            show_intermediate=show_intermediate,
            show_metadata=show_metadata,
        )
        self.chat_history: list[Any] = []

    def chat(self, user_input: str) -> None:
        """Process one user message with streaming output."""
        result = self.runner.run(
            user_input=user_input,
            chat_history=self.chat_history,
            thread_id=self.agent.thread_id,
        )

        # Update history for next turn

        self.chat_history.append({"role": "user", "content": user_input})
        if result.get("output"):
            self.chat_history.append({"role": "assistant", "content": result["output"]})

    def interactive_loop(self) -> None:
        """Run interactive chat loop with streaming output.

        Provides a REPL-style interface for continuous agent interaction.
        """
        terminal_output.print_markdown(
            "# Deep Agent Interactive Session\n\n"
            "Type your requests below. Commands:\n"
            "- `exit` or `quit` or `:q` to exit\n"
            "- `history` to show current conversation\n"
            "- `clear` to start fresh conversation\n"
        )

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in {"exit", "quit", ":q"}:
                    terminal_output.print_info("Goodbye!")
                    break

                if user_input.lower() == "history":
                    self._display_history()
                    continue

                if user_input.lower() == "clear":
                    self.chat_history = []
                    self.agent.thread_id = (
                        f"{self.agent.thread_id.split('_')[0]}_{int(__import__('time').time())}"
                    )
                    terminal_output.print_info("✓ Conversation cleared")
                    continue

                self.chat(user_input)

            except KeyboardInterrupt:
                terminal_output.print_warning("\n⚠️ Interrupted")
                break
            except EOFError:
                break

    def _display_history(self) -> None:
        """Display current conversation history."""
        if not self.chat_history:
            terminal_output.print_info("No messages in history")
            return

        terminal_output.print_info(f"## Conversation History ({len(self.chat_history)} messages)")
        for msg in self.chat_history:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")[:100]
            print(f"**{role}**: {content}...")
