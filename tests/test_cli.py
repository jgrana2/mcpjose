"""Tests for the shared registry CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli


class FakeRegistry:
    def list_tool_specs(self):
        return [{"name": "call_llm", "description": "Generate text."}]

    def call_tool(self, name: str, arguments: dict[str, object]):
        return {"name": name, "arguments": arguments}


def test_cli_tool_list(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "_create_registry", lambda: FakeRegistry())
    monkeypatch.setattr(sys, "argv", ["cli.py", "tool", "list"])

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"name": "call_llm"' in captured.out


def test_cli_tool_call_with_json_and_arg(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_create_registry", lambda: FakeRegistry())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "tool",
            "call",
            "call_llm",
            "--json",
            '{"prompt": "hola"}',
            "--arg",
            "temperature=0",
        ],
    )

    exit_code = cli.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"name": "call_llm"' in captured.out
    assert '"prompt": "hola"' in captured.out
    assert '"temperature": 0' in captured.out
