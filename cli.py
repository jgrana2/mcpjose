"""CLI entry points for the shared MCP Jose tool registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

env_file = Path(__file__).resolve().parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.utils import load_text_file  # noqa: E402
from langchain_agent.tool_registry import ProjectToolRegistry  # noqa: E402

try:
    from cli_workflow import add_workflow_parser, handle_workflow_command

    _HAS_WORKFLOW = True
except ImportError:
    _HAS_WORKFLOW = False

try:
    from cli_team import add_team_parser, handle_team_command

    _HAS_TEAM = True
except ImportError:
    _HAS_TEAM = False


def _create_registry() -> ProjectToolRegistry:
    return ProjectToolRegistry(repo_root=Path(__file__).resolve().parent)


def _emit_output(result: Any) -> None:
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return
    print(result)


def _parse_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false", "null"}:
        return json.loads(lowered)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_key_value_args(pairs: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid --arg '{pair}'. Expected key=value.")
        key, raw_value = pair.split("=", 1)
        if not key:
            raise ValueError(f"Invalid --arg '{pair}'. Key cannot be empty.")
        arguments[key] = _parse_value(raw_value)
    return arguments


def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    return _create_registry().call_tool(name, arguments)


def _extract_text_result(result: Any) -> Any:
    if isinstance(result, dict):
        return result.get("text", result)
    return result


def _load_ocr_context(ocr_context: str | None, ocr_file: str | None) -> str | None:
    if ocr_file:
        return load_text_file(ocr_file)
    return ocr_context


def _write_output_file(
    path: str, content: Any, message: str = "Saved to {path}"
) -> None:
    Path(path).write_text(str(content), encoding="utf-8")
    print(message.format(path=path))


def _emit_text_or_write_output(
    result: Any,
    output_path: str | None = None,
    save_message: str = "Saved to {path}",
) -> None:
    text = _extract_text_result(result)
    if output_path:
        _write_output_file(output_path, text, save_message)
        return
    print(text)


def _build_vision_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("image_path", help="Path to image or PDF")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--ocr-context", default=None, help="OCR context text")
    parser.add_argument("--ocr-file", default=None, help="Path to OCR context file")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--model", default=None, help="Model name")
    return parser


def _run_vision_main(tool_name: str, description: str) -> None:
    parser = _build_vision_parser(description)
    args = parser.parse_args()
    result = _call_tool(
        tool_name,
        {
            "image_path": args.image_path,
            "prompt": args.prompt,
            "ocr_context": _load_ocr_context(args.ocr_context, args.ocr_file),
            "model": args.model,
        },
    )
    _emit_text_or_write_output(result, args.output)


def call_llm_main() -> None:
    """Legacy CLI entry point for OpenAI LLM."""
    parser = argparse.ArgumentParser(description="Call OpenAI API with a prompt")
    parser.add_argument("prompt", help="The prompt to send")
    args = parser.parse_args()
    result = _call_tool("call_llm", {"prompt": args.prompt})
    print(_extract_text_result(result))


def openai_vision_main() -> None:
    """Legacy CLI entry point for OpenAI Vision."""
    _run_vision_main("openai_vision_tool", "Process images with OpenAI Vision")


def gemini_vision_main() -> None:
    """Legacy CLI entry point for Gemini Vision."""
    _run_vision_main("gemini_vision_tool", "Process images with Gemini Vision")


def google_ocr_main() -> None:
    """Legacy CLI entry point for Google OCR."""
    parser = argparse.ArgumentParser(description="Extract text with Google OCR")
    parser.add_argument("input_file", help="Path to image or PDF")
    parser.add_argument("--type", choices=["pdf", "image"], help="File type")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    result = _call_tool(
        "google_ocr",
        {
            "input_file": args.input_file,
            "file_type": args.type,
            "output": args.output,
        },
    )
    annotations = result.get("annotations", [])
    print(f"Extracted {len(annotations)} text elements")
    if args.output:
        print(f"Saved to {args.output}")


def generate_image_main() -> None:
    """Legacy CLI entry point for image generation."""
    parser = argparse.ArgumentParser(description="Generate image with Gemini")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--output", default=None, help="Output path")
    args = parser.parse_args()

    result = _call_tool(
        "generate_image",
        {"prompt": args.prompt, "output_path": args.output},
    )
    if "text" in result:
        print(result["text"])
    if "image_path" in result:
        print(f"Image saved to: {result['image_path']}")


def transcribe_audio_main() -> None:
    """Legacy CLI entry point for audio transcription."""
    parser = argparse.ArgumentParser(description="Transcribe audio with OpenAI Whisper")
    parser.add_argument("audio_path", help="Path to audio file")
    parser.add_argument("--model", default="gpt-4o-transcribe", help="Model to use")
    parser.add_argument("--language", default=None, help="Language code (e.g., en, es)")
    parser.add_argument(
        "--format",
        default="text",
        help="Response format (text, json, verbose_json, srt, vtt)",
    )
    parser.add_argument(
        "--timestamps", action="store_true", help="Include word-level timestamps"
    )
    parser.add_argument(
        "--prompt", default=None, help="Context hint for better accuracy"
    )
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    result = _call_tool(
        "transcribe_audio",
        {
            "audio_path": args.audio_path,
            "model": args.model,
            "language": args.language,
            "response_format": args.format,
            "timestamp_granularities": ["word"] if args.timestamps else None,
            "prompt": args.prompt,
        },
    )

    if args.format == "text":
        output = _extract_text_result(result)
    else:
        output = json.dumps(result, indent=2, ensure_ascii=False, default=str)

    if args.output:
        _write_output_file(args.output, output)
        return

    print(output)


def google_maps_search_main() -> None:
    """Legacy CLI entry point for Google Maps Places search."""
    parser = argparse.ArgumentParser(
        description="Search places using Google Maps Places API"
    )
    parser.add_argument(
        "query", help="Search query (e.g., 'coffee shop', 'restaurants')"
    )
    parser.add_argument(
        "--location", default=None, help="Location bias as 'lat,lng' or address"
    )
    parser.add_argument(
        "--radius", type=int, default=None, help="Search radius in meters"
    )
    parser.add_argument(
        "--type", default=None, help="Place type filter (e.g., 'cafe', 'restaurant')"
    )
    parser.add_argument(
        "--max-results", type=int, default=5, help="Maximum results to return"
    )
    parser.add_argument("--output", default=None, help="Output file path (JSON format)")
    args = parser.parse_args()

    result = _call_tool(
        "search_places",
        {
            "query": args.query,
            "location": args.location,
            "radius": args.radius,
            "place_type": args.type,
            "max_results": args.max_results,
        },
    )

    if args.output:
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"Saved results to {args.output}")
        return

    if not result.get("success"):
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        raise SystemExit(1)

    places = result.get("results", [])
    print(f"Found {len(places)} places for '{args.query}':")
    for index, place in enumerate(places, 1):
        print(f"\n{index}. {place.get('name', 'Unknown')}")
        print(f"   Address: {place.get('address', 'N/A')}")
        print(
            f"   Rating: {place.get('rating', 'N/A')} ({place.get('user_ratings_total', 0)} reviews)"
        )
        print(f"   Place ID: {place.get('place_id', 'N/A')}")
        print(f"   Types: {', '.join(place.get('types', []))}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MCP Jose CLI Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    tool_parser = subparsers.add_parser(
        "tool", help="Call tools from the shared MCP Jose registry"
    )
    tool_subparsers = tool_parser.add_subparsers(
        dest="tool_command", help="Tool commands"
    )

    tool_subparsers.add_parser("list", help="List all shared tools")

    call_parser = tool_subparsers.add_parser(
        "call", help="Call a shared tool by name with JSON or key=value arguments"
    )
    call_parser.add_argument("name", help="Shared tool name")
    call_parser.add_argument(
        "--json",
        dest="json_payload",
        default=None,
        help="JSON object with tool arguments",
    )
    call_parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Tool argument as key=value. Repeat for multiple arguments.",
    )

    webhook_parser = subparsers.add_parser(
        "webhook", help="Run webhook server (WhatsApp + MercadoPago)"
    )
    webhook_parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    webhook_parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )
    webhook_parser.add_argument(
        "--db-path", default=None, help="Path to SQLite database"
    )

    if _HAS_WORKFLOW:
        add_workflow_parser(subparsers)

    if _HAS_TEAM:
        add_team_parser(subparsers)

    return parser


def main() -> int:
    """Main CLI entry point with registry-backed subcommands."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "tool":
        registry = _create_registry()

        if args.tool_command == "list":
            _emit_output(registry.list_tool_specs())
            return 0

        if args.tool_command == "call":
            try:
                arguments: dict[str, Any] = {}
                if args.json_payload:
                    payload = json.loads(args.json_payload)
                    if not isinstance(payload, dict):
                        raise ValueError("--json payload must decode to an object")
                    arguments.update(payload)
                arguments.update(_parse_key_value_args(args.arg))
                result = registry.call_tool(args.name, arguments)
            except Exception as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1

            _emit_output(result)
            return 0

        tool_help = build_parser()._subparsers._group_actions[0].choices["tool"]
        tool_help.print_help()
        return 1

    if args.command == "workflow" and _HAS_WORKFLOW:
        return handle_workflow_command(args)

    if args.command == "team" and _HAS_TEAM:
        return handle_team_command(args)

    if args.command == "webhook":
        from tools.webhook_server import run_webhook_server

        db_path = Path(args.db_path) if getattr(args, "db_path", None) else None

        print(f"Starting webhook server on {args.host}:{args.port}")
        print(f"Database: {db_path or 'auth/whatsapp_messages.sqlite'}")
        print("\nRoutes:")
        print("  WhatsApp  →  GET/POST https://your-domain/webhook")
        print("  MercadoPago → POST  https://your-domain/webhooks/mercadopago")
        print("\nPress Ctrl+C to stop")

        try:
            run_webhook_server(host=args.host, port=args.port, db_path=db_path)
        except KeyboardInterrupt:
            print("\nShutting down...")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
