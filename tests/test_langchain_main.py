"""Tests for the langchain_agent CLI and interactive runner."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent import interactive_runner
from langchain_agent import main as langchain_main
from langchain_agent import terminal_output


class FakeAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    def run(self, prompt: str, chat_history: list[object] | None = None) -> str:
        history = list(chat_history or [])
        self.calls.append((prompt, history))
        return f"echo:{prompt}"


def test_run_interactive_loop_preserves_history() -> None:
    prompts = iter(["first question", "second question", "quit"])
    output = StringIO()
    agent = FakeAgent()

    exit_code = interactive_runner.run_interactive_loop(
        agent=agent,
        input_func=lambda _: next(prompts),
        output_stream=output,
    )

    assert exit_code == 0
    assert [call[0] for call in agent.calls] == ["first question", "second question"]
    assert agent.calls[0][1] == []
    assert len(agent.calls[1][1]) == 2
    rendered = output.getvalue()
    assert "Interactive terminal mode" in rendered
    assert "Assistant> echo:first question" in rendered
    assert "Assistant> echo:second question" in rendered


def test_run_interactive_loop_renders_assistant_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = iter(["first question", "quit"])
    output = StringIO()
    agent = FakeAgent()
    rendered_calls: list[tuple[str, object]] = []

    def fake_print_markdown(text: str, *, output_stream: object) -> None:
        rendered_calls.append((text, output_stream))

    monkeypatch.setattr(terminal_output, "print_markdown", fake_print_markdown)

    exit_code = interactive_runner.run_interactive_loop(
        agent=agent,
        input_func=lambda _: next(prompts),
        output_stream=output,
    )

    assert exit_code == 0
    assert rendered_calls == [("echo:first question", output)]


def test_main_renders_prompt_output_as_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakeMainAgent:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def run(self, prompt: str) -> str:
            assert prompt == "prompt text"
            return "# Title\n\n- item"

    rendered_calls: list[tuple[str, object]] = []

    def fake_print_markdown(text: str, *, output_stream: object = sys.stdout) -> None:
        rendered_calls.append((text, output_stream))

    fake_agent_module = type(sys)("langchain_agent.agent")
    fake_agent_module.MCPJoseLangChainAgent = FakeMainAgent
    monkeypatch.setitem(sys.modules, "langchain_agent.agent", fake_agent_module)
    monkeypatch.setattr(terminal_output, "print_markdown", fake_print_markdown)
    monkeypatch.setattr(sys, "argv", ["langchain_agent.main", "prompt text"])

    exit_code = langchain_main.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert rendered_calls == [("# Title\n\n- item", sys.stdout)]


def test_run_interactive_loop_voice_mode_uses_transcript_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prompts = iter(["", "quit"])
    output = StringIO()
    agent = FakeAgent()
    audio_path = tmp_path / "voice.wav"
    audio_path.write_bytes(b"audio")
    calls: dict[str, object] = {}

    def fake_select_voice_input(*args: object, **kwargs: object) -> str:
        calls["selected"] = True
        return ":2"

    def fake_record_voice_prompt(*args: object, **kwargs: object) -> Path:
        calls["recorded"] = True
        calls["voice_input"] = kwargs.get("voice_input")
        return audio_path

    def fake_transcribe_voice_prompt(
        agent_arg: object, path_arg: object
    ) -> str:
        calls["transcribed"] = path_arg
        assert agent_arg is agent
        return "spoken prompt"

    monkeypatch.setattr(
        interactive_runner, "_select_voice_input", fake_select_voice_input
    )
    monkeypatch.setattr(
        interactive_runner, "_record_voice_prompt", fake_record_voice_prompt
    )
    monkeypatch.setattr(
        interactive_runner, "_transcribe_voice_prompt", fake_transcribe_voice_prompt
    )

    exit_code = interactive_runner.run_interactive_loop(
        agent=agent,
        input_func=lambda _: next(prompts),
        output_stream=output,
        voice_mode=True,
    )

    assert exit_code == 0
    assert [call[0] for call in agent.calls] == ["spoken prompt"]
    assert calls["selected"] is True
    assert calls["recorded"] is True
    assert calls["voice_input"] == ":2"
    assert calls["transcribed"] == audio_path
    assert not audio_path.exists()
    rendered = output.getvalue()
    assert "Voice mode is enabled" in rendered
    assert "Voice> spoken prompt" in rendered


def test_record_voice_prompt_disconnects_subprocess_stdin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = StringIO()
    audio_path = tmp_path / "recorded.wav"
    captured: dict[str, object] = {}

    class FakeProcess:
        def poll(self) -> None:
            return None

        def communicate(self, timeout: int = 5):
            return (b"", b"")

        def kill(self) -> None:
            return None

        def send_signal(self, sig: object) -> None:
            return None

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["stdin"] = kwargs.get("stdin")
        Path(command[-1]).write_bytes(b"audio")
        return FakeProcess()

    monkeypatch.setattr(interactive_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(interactive_runner, "_stop_voice_process", lambda process: "")
    monkeypatch.setattr(
        interactive_runner,
        "_build_voice_recording_command",
        lambda output, voice_input=":0": (
            ["ffmpeg", "-nostdin", "-y", voice_input, str(output)],
            "ffmpeg",
        ),
    )

    result = interactive_runner._record_voice_prompt(
        input_func=lambda _: "",
        output_stream=output,
    )

    assert result.exists()
    assert captured["stdin"] is interactive_runner.subprocess.DEVNULL
    assert "-nostdin" in captured["command"]


def test_main_interactive_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_loop(**kwargs: object) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(langchain_main, "run_interactive_loop", fake_run_interactive_loop)
    monkeypatch.setattr(sys, "argv", ["langchain_agent.main", "--interactive", "--model", "test-model"])

    exit_code = langchain_main.main()

    assert exit_code == 0
    assert captured["model"] == "test-model"
    assert captured["temperature"] == 0.0
    assert captured["max_iterations"] == 12


def test_main_voice_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_loop(**kwargs: object) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(langchain_main, "run_interactive_loop", fake_run_interactive_loop)
    monkeypatch.setattr(
        sys,
        "argv",
        ["langchain_agent.main", "--interactive", "--voice"],
    )

    exit_code = langchain_main.main()

    assert exit_code == 0
    assert captured["voice_mode"] is True


def test_main_rejects_prompt_with_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["langchain_agent.main", "prompt text", "--interactive"],
    )

    with pytest.raises(SystemExit) as exc_info:
        langchain_main.main()

    assert exc_info.value.code == 2
