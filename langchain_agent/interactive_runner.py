"""Terminal interactive interface for the MCP Jose LangChain agent."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Optional, TextIO

from .agent import MCPJoseLangChainAgent

try:
    from langchain_core.messages import AIMessage, HumanMessage
except Exception:  # pragma: no cover - dependency guard
    AIMessage = None
    HumanMessage = None


TERMINAL_EXIT_COMMANDS = {"exit", "quit", ":q"}


def _append_turn(history: list[Any], prompt: str, response: str) -> list[Any]:
    if HumanMessage is None or AIMessage is None:
        return history

    return history + [HumanMessage(content=prompt), AIMessage(content=response)]


def run_interactive_loop(
    *,
    agent: Optional[MCPJoseLangChainAgent] = None,
    repo_root: Optional[Path] = None,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.0,
    max_iterations: int = 12,
    verbose: bool = False,
    history_turn_limit: int = 12,
    input_func: Callable[[str], str] = input,
    output_stream: TextIO = sys.stdout,
) -> int:
    """Run a terminal REPL for the LangChain agent."""
    if agent is None:
        resolved_root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
        agent = MCPJoseLangChainAgent(
            repo_root=resolved_root,
            model=model,
            temperature=temperature,
            max_iterations=max_iterations,
            verbose=verbose,
        )

    history: list[Any] = []
    max_messages = max(history_turn_limit, 0) * 2

    print(
        "Interactive terminal mode. Type your prompt and press Enter. "
        "Use 'exit', 'quit', or Ctrl-D to stop.",
        file=output_stream,
    )

    while True:
        try:
            prompt = input_func("You> ")
        except EOFError:
            print("\nExiting interactive mode.", file=output_stream)
            return 0
        except KeyboardInterrupt:
            print("\nExiting interactive mode.", file=output_stream)
            return 0

        user_input = prompt.strip()
        if not user_input:
            continue

        if user_input.lower() in TERMINAL_EXIT_COMMANDS:
            print("Exiting interactive mode.", file=output_stream)
            return 0

        try:
            response = agent.run(user_input, chat_history=history).strip()
        except KeyboardInterrupt:
            print("\nExiting interactive mode.", file=output_stream)
            return 0
        except Exception as exc:
            print(f"Agent execution failed: {exc}", file=output_stream)
            continue

        if not response:
            response = "(no response)"

        print(f"Assistant> {response}", file=output_stream)
        history = _append_turn(history, user_input, response)
        if max_messages and len(history) > max_messages:
            history = history[-max_messages:]
