"""Tests for the shared registry CLI."""

from __future__ import annotations

import json
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


class RecordingRegistry:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call_tool(self, name: str, arguments: dict[str, object]):
        self.calls.append((name, arguments))
        return self.result


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


def test_call_llm_main_preserves_text_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry({"text": "hola mundo"})
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(sys, "argv", ["call_llm.py", "describe this"])

    cli.call_llm_main()

    captured = capsys.readouterr()
    assert registry.calls == [("call_llm", {"prompt": "describe this"})]
    assert captured.out == "hola mundo\n"


def test_openai_vision_main_uses_ocr_file_and_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    registry = RecordingRegistry({"text": "vision result"})
    ocr_file = tmp_path / "context.txt"
    output_file = tmp_path / "result.txt"
    ocr_file.write_text("ocr text", encoding="utf-8")
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "openai_vision.py",
            "image.png",
            "summarize",
            "--ocr-file",
            str(ocr_file),
            "--output",
            str(output_file),
            "--model",
            "gpt-4.1",
        ],
    )

    cli.openai_vision_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "openai_vision_tool",
            {
                "image_path": "image.png",
                "prompt": "summarize",
                "ocr_context": "ocr text",
                "model": "gpt-4.1",
            },
        )
    ]
    assert output_file.read_text(encoding="utf-8") == "vision result"
    assert captured.out == f"Saved to {output_file}\n"


def test_gemini_vision_main_preserves_stdout_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry({"text": "gemini result"})
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_vllm.py", "scan.pdf", "extract", "--ocr-context", "prior text"],
    )

    cli.gemini_vision_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "gemini_vision_tool",
            {
                "image_path": "scan.pdf",
                "prompt": "extract",
                "ocr_context": "prior text",
                "model": None,
            },
        )
    ]
    assert captured.out == "gemini result\n"


def test_google_ocr_main_preserves_summary_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry({"annotations": [{"text": "a"}, {"text": "b"}]})
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(
        sys,
        "argv",
        ["google_vision_ocr.py", "doc.pdf", "--type", "pdf", "--output", "out.json"],
    )

    cli.google_ocr_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "google_ocr",
            {"input_file": "doc.pdf", "file_type": "pdf", "output": "out.json"},
        )
    ]
    assert captured.out == "Extracted 2 text elements\nSaved to out.json\n"


def test_generate_image_main_preserves_field_based_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry(
        {"text": "generation complete", "image_path": "/tmp/generated.png"}
    )
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(sys, "argv", ["generate_image.py", "a red fox", "--output", "fox.png"])

    cli.generate_image_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        ("generate_image", {"prompt": "a red fox", "output_path": "fox.png"})
    ]
    assert captured.out == "generation complete\nImage saved to: /tmp/generated.png\n"


def test_transcribe_audio_main_preserves_text_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry({"text": "hello world"})
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transcribe_audio.py",
            "audio.mp3",
            "--language",
            "en",
            "--timestamps",
            "--prompt",
            "meeting notes",
        ],
    )

    cli.transcribe_audio_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "transcribe_audio",
            {
                "audio_path": "audio.mp3",
                "model": "gpt-4o-transcribe",
                "language": "en",
                "response_format": "text",
                "timestamp_granularities": ["word"],
                "prompt": "meeting notes",
            },
        )
    ]
    assert captured.out == "hello world\n"


def test_transcribe_audio_main_preserves_json_output_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    registry = RecordingRegistry({"segments": [{"text": "hello"}], "language": "en"})
    output_file = tmp_path / "transcript.json"
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transcribe_audio.py",
            "audio.mp3",
            "--format",
            "verbose_json",
            "--output",
            str(output_file),
        ],
    )

    cli.transcribe_audio_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "transcribe_audio",
            {
                "audio_path": "audio.mp3",
                "model": "gpt-4o-transcribe",
                "language": None,
                "response_format": "verbose_json",
                "timestamp_granularities": None,
                "prompt": None,
            },
        )
    ]
    assert json.loads(output_file.read_text(encoding="utf-8")) == {
        "segments": [{"text": "hello"}],
        "language": "en",
    }
    assert captured.out == f"Saved to {output_file}\n"


def test_google_maps_search_main_preserves_pretty_print(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry(
        {
            "success": True,
            "results": [
                {
                    "name": "Cafe Central",
                    "address": "Main St 1",
                    "rating": 4.7,
                    "user_ratings_total": 120,
                    "place_id": "abc123",
                    "types": ["cafe", "food"],
                }
            ],
        }
    )
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(sys, "argv", ["maps.py", "coffee", "--max-results", "3"])

    cli.google_maps_search_main()

    captured = capsys.readouterr()
    assert registry.calls == [
        (
            "search_places",
            {
                "query": "coffee",
                "location": None,
                "radius": None,
                "place_type": None,
                "max_results": 3,
            },
        )
    ]
    assert "Found 1 places for 'coffee':" in captured.out
    assert "Cafe Central" in captured.out
    assert "Rating: 4.7 (120 reviews)" in captured.out


def test_google_maps_search_main_preserves_error_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = RecordingRegistry({"success": False, "error": "boom"})
    monkeypatch.setattr(cli, "_create_registry", lambda: registry)
    monkeypatch.setattr(sys, "argv", ["maps.py", "coffee"])

    with pytest.raises(SystemExit) as exc:
        cli.google_maps_search_main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert captured.err == "Error: boom\n"
