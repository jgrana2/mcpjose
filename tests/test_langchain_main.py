"""Tests for the langchain_agent CLI and interactive runner."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent import interactive_runner
from langchain_agent import main as langchain_main


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


def test_main_rejects_prompt_with_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["langchain_agent.main", "prompt text", "--interactive"],
    )

    with pytest.raises(SystemExit) as exc_info:
        langchain_main.main()

    assert exc_info.value.code == 2