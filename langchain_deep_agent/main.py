"""CLI entry point for the MCP Jose Deep Agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import terminal_output
from .context import ProjectContextLoader
from .interactive_runner import run_interactive_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MCP Jose Deep Agent")
    parser.add_argument("prompt", nargs="?", help="Task prompt")
    parser.add_argument(
        "--model", default="gpt-5.4-mini", help="OpenAI model for LangChain"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Model temperature"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=12, help="Agent iteration cap"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable LangChain verbose logs"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the Deep Agent in an interactive terminal session",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable push-to-talk voice input in interactive mode",
    )
    parser.add_argument(
        "--whatsapp",
        action="store_true",
        help="Run the WhatsApp-only agent loop",
    )
    parser.add_argument(
        "--whatsapp-allowed-sender",
        default=None,
        help="Only process messages from this WhatsApp number",
    )
    parser.add_argument(
        "--whatsapp-poll-seconds",
        type=int,
        default=3,
        help="WhatsApp polling interval in seconds",
    )
    parser.add_argument(
        "--list-tools", action="store_true", help="List registered tool names"
    )
    parser.add_argument(
        "--list-skills", action="store_true", help="List discovered skills"
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print AGENTS.md + skills prompt context and exit",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.whatsapp:
        try:
            from .whatsapp_runner import run_whatsapp_loop

            run_whatsapp_loop(
                model=args.model,
                temperature=args.temperature,
                max_iterations=args.max_iterations,
                verbose=args.verbose,
                allowed_sender=args.whatsapp_allowed_sender,
                poll_seconds=args.whatsapp_poll_seconds,
                repo_root=repo_root,
            )
            return 0
        except KeyboardInterrupt:
            return 0

    if args.voice and not args.interactive:
        parser.error("--voice requires --interactive")

    if args.interactive:
        if args.prompt:
            parser.error("prompt cannot be used together with --interactive")

        try:
            return run_interactive_loop(
                repo_root=repo_root,
                model=args.model,
                temperature=args.temperature,
                max_iterations=args.max_iterations,
                verbose=args.verbose,
                voice_mode=args.voice,
            )
        except Exception as exc:
            print(f"Failed to initialize interactive Deep Agent: {exc}", file=sys.stderr)
            return 1

    if args.show_context:
        loader = ProjectContextLoader(repo_root=repo_root)
        print(loader.build_agent_context())
        return 0

    try:
        from .agent import MCPJoseLangChainDeepAgent

        agent = MCPJoseLangChainDeepAgent(
            repo_root=repo_root,
            model=args.model,
            temperature=args.temperature,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"Failed to initialize Deep Agent: {exc}", file=sys.stderr)
        return 1

    if args.list_tools:
        for name in agent.list_tool_names():
            print(name)
        return 0

    if args.list_skills:
        skills = agent.list_skills().get("skills", [])
        for skill in skills:
            print(f"{skill['skill_id']}: {skill['description']}")
        return 0

    if not args.prompt:
        parser.error(
            "prompt is required unless --interactive, --whatsapp, --list-tools, --list-skills, or --show-context is used"
        )

    try:
        terminal_output.print_markdown(agent.run(args.prompt))
        return 0
    except Exception as exc:
        print(f"Agent execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
