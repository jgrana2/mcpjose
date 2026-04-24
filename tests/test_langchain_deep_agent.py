"""Tests for langchain_deep_agent CLI parity with the ReAct agent."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.agent import MCPJoseLangChainAgent
from langchain_agent.context import ProjectContextLoader
from langchain_deep_agent import interactive_runner
from langchain_deep_agent.agent import MCPJoseLangChainDeepAgent
from langchain_deep_agent import main as deep_main
from langchain_deep_agent import terminal_output


class FakeAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    def run(self, prompt: str, chat_history: list[object] | None = None) -> str:
        history = list(chat_history or [])
        self.calls.append((prompt, history))
        return f"echo:{prompt}"


class FakeMainAgent:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def run(self, prompt: str) -> str:
        assert prompt == "prompt text"
        return "# Title\n\n- item"


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

    def fake_transcribe_voice_prompt(agent_arg: object, path_arg: object) -> str:
        calls["transcribed"] = path_arg
        assert agent_arg is agent
        return "spoken prompt"

    monkeypatch.setattr(interactive_runner, "_select_voice_input", fake_select_voice_input)
    monkeypatch.setattr(interactive_runner, "_record_voice_prompt", fake_record_voice_prompt)
    monkeypatch.setattr(interactive_runner, "_transcribe_voice_prompt", fake_transcribe_voice_prompt)
    monkeypatch.setattr(interactive_runner.react_interactive_runner, "_select_voice_input", fake_select_voice_input)
    monkeypatch.setattr(interactive_runner.react_interactive_runner, "_record_voice_prompt", fake_record_voice_prompt)
    monkeypatch.setattr(interactive_runner.react_interactive_runner, "_transcribe_voice_prompt", fake_transcribe_voice_prompt)

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


def test_main_renders_prompt_output_as_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rendered_calls: list[tuple[str, object]] = []

    def fake_print_markdown(text: str, *, output_stream: object = sys.stdout) -> None:
        rendered_calls.append((text, output_stream))

    fake_agent_module = type(sys)("langchain_deep_agent.agent")
    fake_agent_module.MCPJoseLangChainDeepAgent = FakeMainAgent
    monkeypatch.setitem(sys.modules, "langchain_deep_agent.agent", fake_agent_module)
    monkeypatch.setattr(terminal_output, "print_markdown", fake_print_markdown)
    monkeypatch.setattr(sys, "argv", ["langchain_deep_agent.main", "prompt text"])

    exit_code = deep_main.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert rendered_calls == [("# Title\n\n- item", sys.stdout)]


def test_main_interactive_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_interactive_loop(**kwargs: object) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(deep_main, "run_interactive_loop", fake_run_interactive_loop)
    monkeypatch.setattr(
        sys,
        "argv",
        ["langchain_deep_agent.main", "--interactive", "--voice", "--model", "test-model"],
    )

    exit_code = deep_main.main()

    assert exit_code == 0
    assert captured["model"] == "test-model"
    assert captured["temperature"] == 0.0
    assert captured["max_iterations"] == 12
    assert captured["voice_mode"] is True


def test_main_rejects_prompt_with_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["langchain_deep_agent.main", "prompt text", "--interactive"],
    )

    with pytest.raises(SystemExit) as exc_info:
        deep_main.main()

    assert exc_info.value.code == 2


def test_deep_agent_registers_memory_and_skills(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Rules\nUse tools first.", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("# Memory\nRemember decisions.", encoding="utf-8")
    skill_dir = tmp_path / ".agents" / "skills" / "clock"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Clock\nHandle time questions.", encoding="utf-8")

    captured: dict[str, Any] = {}

    class FakeMemorySaver:
        pass

    class FakeDeepRuntime:
        def invoke(self, payload: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
            return {"messages": [{"role": "assistant", "content": "ok"}], "payload": payload, "config": config}

        def stream(self, payload: dict[str, Any], config: dict[str, Any] | None = None):
            yield {"payload": payload, "config": config}

    def fake_base_init(
        self: MCPJoseLangChainDeepAgent,
        repo_root: Path | None = None,
        model: str = "gpt-5.4-mini",
        temperature: float = 0.0,
        max_iterations: int = 12,
        verbose: bool = False,
    ) -> None:
        self.repo_root = (repo_root or tmp_path).resolve()
        self.model = model
        self.context_loader = ProjectContextLoader(self.repo_root)
        self.tools = ["demo-tool"]
        self.system_prompt = "base prompt"
        self.verbose = verbose

    def fake_create_deep_agent(**kwargs: Any) -> FakeDeepRuntime:
        captured.update(kwargs)
        return FakeDeepRuntime()

    monkeypatch.setattr(MCPJoseLangChainAgent, "__init__", fake_base_init)
    monkeypatch.setattr("langchain_deep_agent.agent.MemorySaver", FakeMemorySaver)
    monkeypatch.setattr("langchain_deep_agent.agent.create_deep_agent", fake_create_deep_agent)

    agent = MCPJoseLangChainDeepAgent(repo_root=tmp_path)

    assert captured["memory"] == ["/AGENTS.md", "/MEMORY.md"]
    assert captured["skills"] == ["/skills/"]
    assert isinstance(captured["checkpointer"], FakeMemorySaver)
    assert "/AGENTS.md" in agent._virtual_files
    assert "/MEMORY.md" in agent._virtual_files
    assert "/skills/clock/SKILL.md" in agent._virtual_files


def test_deep_agent_payload_includes_virtual_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "AGENTS.md").write_text("# Rules\nUse tools first.", encoding="utf-8")
    skill_dir = tmp_path / ".agents" / "skills" / "clock"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Clock\nHandle time questions.", encoding="utf-8")

    invoke_calls: list[dict[str, Any]] = []

    class FakeDeepRuntime:
        def invoke(self, payload: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
            invoke_calls.append({"payload": payload, "config": config})
            return {"messages": [{"role": "assistant", "content": "tool-backed response"}]}

        def stream(self, payload: dict[str, Any], config: dict[str, Any] | None = None):
            yield {"payload": payload, "config": config}

    def fake_base_init(
        self: MCPJoseLangChainDeepAgent,
        repo_root: Path | None = None,
        model: str = "gpt-5.4-mini",
        temperature: float = 0.0,
        max_iterations: int = 12,
        verbose: bool = False,
    ) -> None:
        self.repo_root = (repo_root or tmp_path).resolve()
        self.model = model
        self.context_loader = ProjectContextLoader(self.repo_root)
        self.tools = ["demo-tool"]
        self.system_prompt = "base prompt"
        self.verbose = verbose

    monkeypatch.setattr(MCPJoseLangChainAgent, "__init__", fake_base_init)
    monkeypatch.setattr("langchain_deep_agent.agent.MemorySaver", lambda: object())
    monkeypatch.setattr("langchain_deep_agent.agent.create_deep_agent", lambda **kwargs: FakeDeepRuntime())

    agent = MCPJoseLangChainDeepAgent(repo_root=tmp_path)
    result = agent.invoke("what time is it?")

    assert result["output"] == "tool-backed response"
    assert invoke_calls
    assert invoke_calls[0]["payload"]["messages"] == [{"role": "user", "content": "what time is it?"}]
    assert "/AGENTS.md" in invoke_calls[0]["payload"]["files"]
    assert "/skills/clock/SKILL.md" in invoke_calls[0]["payload"]["files"]
