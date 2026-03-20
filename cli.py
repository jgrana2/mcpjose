"""Simplified CLI entry points for direct tool execution."""

# Load environment variables FIRST (before any other imports)
import sys
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv

env_file = Path(__file__).resolve().parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)

import argparse  # noqa: E402

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.utils import load_text_file  # noqa: E402
from providers import ProviderFactory  # noqa: E402


def call_llm_main():
    """CLI entry point for OpenAI LLM."""
    parser = argparse.ArgumentParser(description="Call OpenAI API with a prompt")
    parser.add_argument("prompt", help="The prompt to send")
    args = parser.parse_args()

    provider = ProviderFactory.create_llm("openai")
    print(provider.complete(args.prompt))


def openai_vision_main():
    """CLI entry point for OpenAI Vision."""
    parser = argparse.ArgumentParser(description="Process images with OpenAI Vision")
    parser.add_argument("image_path", help="Path to image or PDF")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--ocr-context", default=None, help="OCR context text")
    parser.add_argument("--ocr-file", default=None, help="Path to OCR context file")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--model", default=None, help="Model name")

    args = parser.parse_args()

    ocr_context = args.ocr_context
    if args.ocr_file:
        ocr_context = load_text_file(args.ocr_file)

    provider = ProviderFactory.create_vision("openai")
    result = provider.process_image(
        args.image_path,
        args.prompt,
        ocr_context,
        model=args.model,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Saved to {args.output}")
    else:
        print(result)


def gemini_vision_main():
    """CLI entry point for Gemini Vision."""
    parser = argparse.ArgumentParser(description="Process images with Gemini Vision")
    parser.add_argument("image_path", help="Path to image or PDF")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--ocr-context", default=None, help="OCR context text")
    parser.add_argument("--ocr-file", default=None, help="Path to OCR context file")
    parser.add_argument("--output", default=None, help="Output file path")

    args = parser.parse_args()

    ocr_context = args.ocr_context
    if args.ocr_file:
        ocr_context = load_text_file(args.ocr_file)

    provider = ProviderFactory.create_vision("gemini")
    result = provider.process_image(args.image_path, args.prompt, ocr_context)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Saved to {args.output}")
    else:
        print(result)


def google_ocr_main():
    """CLI entry point for Google OCR."""
    parser = argparse.ArgumentParser(description="Extract text with Google OCR")
    parser.add_argument("input_file", help="Path to image or PDF")
    parser.add_argument("--type", choices=["pdf", "image"], help="File type")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    provider = ProviderFactory.create_ocr("google")
    annotations = provider.extract_text(args.input_file, args.type)

    print(f"Extracted {len(annotations)} text elements")

    if args.output:
        provider.save_annotations(annotations, args.output)
        print(f"Saved to {args.output}")


def generate_image_main():
    """CLI entry point for image generation."""
    parser = argparse.ArgumentParser(description="Generate image with Gemini")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--output", default=None, help="Output path")

    args = parser.parse_args()

    provider = ProviderFactory.create_image_generator("gemini")
    result = provider.generate(args.prompt, args.output)

    if "text" in result:
        print(result["text"])
    if "image_path" in result:
        print(f"Image saved to: {result['image_path']}")


def transcribe_audio_main():
    """CLI entry point for audio transcription."""
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

    provider = ProviderFactory.create_transcription("openai")

    kwargs = {"model": args.model, "response_format": args.format}
    if args.language:
        kwargs["language"] = args.language
    if args.timestamps:
        kwargs["timestamp_granularities"] = ["word"]
    if args.prompt:
        kwargs["prompt"] = args.prompt

    try:
        result = provider.transcribe(args.audio_path, **kwargs)

        # Format output based on response type
        if args.format == "text":
            output = result if isinstance(result, str) else result.text
        else:
            import json

            if hasattr(result, "model_dump"):
                output = json.dumps(result.model_dump(), indent=2)
            elif hasattr(result, "dict"):
                output = json.dumps(result.dict(), indent=2)
            else:
                output = str(result)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Saved to {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def google_maps_search_main():
    """CLI entry point for Google Maps Places search."""
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

    try:
        provider = ProviderFactory.create_maps("google")
        results = provider.search_places(
            query=args.query,
            location=args.location,
            radius=args.radius,
            place_type=args.type,
            max_results=args.max_results,
        )

        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Saved {len(results)} results to {args.output}")
        else:
            print(f"Found {len(results)} places for '{args.query}':")
            for i, place in enumerate(results, 1):
                print(f"\n{i}. {place.get('name', 'Unknown')}")
                print(f"   Address: {place.get('address', 'N/A')}")
                print(
                    f"   Rating: {place.get('rating', 'N/A')} ({place.get('user_ratings_total', 0)} reviews)"
                )
                print(f"   Place ID: {place.get('place_id', 'N/A')}")
                print(f"   Types: {', '.join(place.get('types', []))}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(description="MCP Jose CLI Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # whatsapp-webhook command
    webhook_parser = subparsers.add_parser(
        "whatsapp-webhook", help="Run WhatsApp webhook server to receive messages"
    )
    webhook_parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    webhook_parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )
    webhook_parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite database (default: auth/whatsapp_messages.sqlite)",
    )

    args = parser.parse_args()

    if args.command == "whatsapp-webhook":
        from pathlib import Path
        from tools.whatsapp_webhook import run_webhook_server

        db_path = Path(args.db_path) if args.db_path else None

        print(f"Starting WhatsApp webhook server on {args.host}:{args.port}")
        print(f"Database: {db_path or 'auth/whatsapp_messages.sqlite'}")
        print("\nConfigure webhook URL in Meta Developer dashboard:")
        print("  https://your-domain/webhook")
        print("\nVerify token (set in WHATSAPP_WEBHOOK_VERIFY_TOKEN env var)")
        print("\nPress Ctrl+C to stop")

        try:
            run_webhook_server(host=args.host, port=args.port, db_path=db_path)
        except KeyboardInterrupt:
            print("\nShutting down...")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
