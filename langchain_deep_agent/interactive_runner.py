"""Terminal interactive interface for the MCP Jose Deep Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, TextIO

from langchain_agent import interactive_runner as react_interactive_runner

from .agent import MCPJoseLangChainDeepAgent
from .streaming_runner import InteractiveStreamingSession

TERMINAL_EXIT_COMMANDS = react_interactive_runner.TERMINAL_EXIT_COMMANDS
_append_turn = react_interactive_runner._append_turn
_build_voice_recording_command = react_interactive_runner._build_voice_recording_command
_list_mac_voice_devices = react_interactive_runner._list_mac_voice_devices
_record_voice_prompt = react_interactive_runner._record_voice_prompt
_select_voice_input = react_interactive_runner._select_voice_input
_stop_voice_process = react_interactive_runner._stop_voice_process


def _transcribe_voice_prompt(agent: MCPJoseLangChainDeepAgent, audio_path: Path) -> str:
    result = agent.tool_registry.call_tool(
        "transcribe_audio",
        {"audio_path": str(audio_path)},
    )
    if isinstance(result, dict):
        error = result.get("error")
        if error:
            raise RuntimeError(str(error))
        return str(result.get("text", "")).strip()
    return str(result).strip()


def run_interactive_loop(
    *,
    agent: Optional[MCPJoseLangChainDeepAgent] = None,
    repo_root: Optional[Path] = None,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.0,
    max_iterations: int = 12,
    verbose: bool = False,
    history_turn_limit: int = 12,
    voice_mode: bool = False,
    input_func: Callable[[str], str] = input,
    output_stream: TextIO = None,
) -> int:
    return react_interactive_runner.run_interactive_loop(
        agent=agent,
        repo_root=repo_root,
        model=model,
        temperature=temperature,
        max_iterations=max_iterations,
        verbose=verbose,
        history_turn_limit=history_turn_limit,
        voice_mode=voice_mode,
        input_func=input_func,
        output_stream=output_stream if output_stream is not None else __import__("sys").stdout,
    )


__all__ = [
    "TERMINAL_EXIT_COMMANDS",
    "InteractiveStreamingSession",
    "_append_turn",
    "_build_voice_recording_command",
    "_list_mac_voice_devices",
    "_record_voice_prompt",
    "_select_voice_input",
    "_stop_voice_process",
    "_transcribe_voice_prompt",
    "run_interactive_loop",
]
