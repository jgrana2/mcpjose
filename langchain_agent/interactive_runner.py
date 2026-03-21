"""Terminal interactive interface for the MCP Jose LangChain agent."""

from __future__ import annotations

import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, TextIO
from uuid import uuid4

try:
    from langchain_core.messages import AIMessage, HumanMessage
except Exception:  # pragma: no cover - dependency guard
    AIMessage = None
    HumanMessage = None

from . import terminal_output


TERMINAL_EXIT_COMMANDS = {"exit", "quit", ":q"}


def _append_turn(history: list[Any], prompt: str, response: str) -> list[Any]:
    if HumanMessage is None or AIMessage is None:
        return history

    return history + [HumanMessage(content=prompt), AIMessage(content=response)]


def _list_mac_voice_devices() -> list[tuple[int, str]]:
    """List available macOS audio input devices via ffmpeg."""
    if sys.platform != "darwin" or not shutil.which("ffmpeg"):
        return []

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-f",
            "avfoundation",
            "-list_devices",
            "true",
            "-i",
            "",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    devices: list[tuple[int, str]] = []
    in_audio_section = False
    for raw_line in result.stderr.splitlines():
        line = raw_line.strip()
        if "AVFoundation audio devices:" in line:
            in_audio_section = True
            continue
        if not in_audio_section:
            continue
        if not line:
            if devices:
                break
            continue
        match = re.search(r"\[(\d+)\]\s+(.+)$", line)
        if match:
            devices.append((int(match.group(1)), match.group(2).strip()))

    return devices


def _select_voice_input(input_func: Callable[[str], str], output_stream: TextIO) -> str:
    """Prompt the user to choose a microphone for the session."""
    devices = _list_mac_voice_devices()
    if not devices:
        if sys.platform == "darwin":
            print(
                "Could not list audio devices. Using the default microphone.",
                file=output_stream,
            )
            return ":0"
        print(
            "Device selection is only supported on macOS. Using the default microphone.",
            file=output_stream,
        )
        return "default"

    print("Select a microphone for voice mode:", file=output_stream)
    for index, (device_id, name) in enumerate(devices, start=1):
        print(f"  {index}. {name} (avfoundation :{device_id})", file=output_stream)

    while True:
        choice = input_func("Mic number [1]: ").strip()
        if not choice:
            return f":{devices[0][0]}"

        if choice.isdigit():
            selected = int(choice)
            if 1 <= selected <= len(devices):
                return f":{devices[selected - 1][0]}"

        print("Invalid selection. Enter a number from the list.", file=output_stream)


def _build_voice_recording_command(
    output_path: Path, voice_input: str = ":0"
) -> tuple[list[str], str]:
    """Build a recorder command for the current platform."""
    if shutil.which("ffmpeg"):
        if sys.platform == "darwin":
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-f",
                    "avfoundation",
                    "-i",
                    voice_input,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(output_path),
                ],
                "ffmpeg",
            )
        if sys.platform.startswith("linux"):
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-f",
                    "alsa",
                    "-i",
                    voice_input,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(output_path),
                ],
                "ffmpeg",
            )

    if shutil.which("rec"):
        return (
            [
                "rec",
                "-q",
                "-r",
                "16000",
                "-c",
                "1",
                str(output_path),
            ],
            "rec",
        )

    raise RuntimeError("Voice mode requires ffmpeg or the SoX rec command.")


def _stop_voice_process(process: subprocess.Popen[bytes]) -> str:
    """Stop a recorder process and return captured stderr text."""
    if process.poll() is None:
        if os.name == "nt":
            process.terminate()
        else:
            process.send_signal(signal.SIGINT)

    try:
        _, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        _, stderr = process.communicate(timeout=5)

    return (stderr or b"").decode("utf-8", errors="replace").strip()


def _record_voice_prompt(
    input_func: Callable[[str], str],
    output_stream: TextIO,
    voice_input: str = ":0",
) -> Path:
    """Record one voice prompt to a temporary WAV file."""
    output_path = Path(tempfile.gettempdir()) / f"mcpjose_voice_{uuid4().hex}.wav"
    command, recorder_name = _build_voice_recording_command(output_path, voice_input)
    process: subprocess.Popen[bytes] | None = None

    print(
        f"Recording with {recorder_name}. Press Enter to stop speaking.",
        file=output_stream,
    )

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        input_func("")
    except (EOFError, KeyboardInterrupt):
        if process is not None:
            _stop_voice_process(process)
        raise

    if process is None:
        raise RuntimeError("Failed to start recorder process.")

    stderr = _stop_voice_process(process)
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(stderr or "Recorder finished without producing audio.")

    return output_path


def _transcribe_voice_prompt(agent: MCPJoseLangChainAgent, audio_path: Path) -> str:
    """Transcribe a recorded voice prompt with the existing tool registry."""
    result = agent.tool_registry.call_tool(
        "transcribe_audio",
        {"audio_path": str(audio_path)},
    )
    if isinstance(result, dict):
        error = result.get("error")
        if error:
            raise RuntimeError(str(error))
        text = result.get("text", "")
        return str(text).strip()
    return str(result).strip()


def run_interactive_loop(
    *,
    agent: Optional[MCPJoseLangChainAgent] = None,
    repo_root: Optional[Path] = None,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.0,
    max_iterations: int = 12,
    verbose: bool = False,
    history_turn_limit: int = 12,
    voice_mode: bool = False,
    input_func: Callable[[str], str] = input,
    output_stream: TextIO = sys.stdout,
) -> int:
    """Run a terminal REPL for the LangChain agent."""
    if agent is None:
        from .agent import MCPJoseLangChainAgent

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
    if voice_mode:
        try:
            voice_input = _select_voice_input(input_func, output_stream)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting interactive mode.", file=output_stream)
            return 0
        print(
            "Voice mode is enabled. Press Enter on an empty prompt to record audio.",
            file=output_stream,
        )
    else:
        voice_input = ":0"

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
        if user_input.lower() in TERMINAL_EXIT_COMMANDS:
            print("Exiting interactive mode.", file=output_stream)
            return 0

        if voice_mode and not user_input:
            audio_path: Optional[Path] = None
            try:
                audio_path = _record_voice_prompt(
                    input_func,
                    output_stream,
                    voice_input=voice_input,
                )
                user_input = _transcribe_voice_prompt(agent, audio_path)
                if not user_input:
                    print("No speech detected.", file=output_stream)
                    continue
                print(f"Voice> {user_input}", file=output_stream)
            except EOFError:
                print("\nExiting interactive mode.", file=output_stream)
                return 0
            except KeyboardInterrupt:
                print("\nExiting interactive mode.", file=output_stream)
                return 0
            except Exception as exc:
                print(f"Voice recording failed: {exc}", file=output_stream)
                continue
            finally:
                if audio_path is not None:
                    audio_path.unlink(missing_ok=True)
        elif not user_input:
            continue

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

        terminal_output.print_separator(output_stream=output_stream)
        print("Assistant>", file=output_stream, end=" ")
        terminal_output.print_markdown(response, output_stream=output_stream)
        history = _append_turn(history, user_input, response)
        if max_messages and len(history) > max_messages:
            history = history[-max_messages:]
