"""CLI entry point for the MCP Jose LangChain agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import MCPJoseLangChainAgent
from .context import ProjectContextLoader

try:
    from langchain_core.messages import AIMessage, HumanMessage
except Exception:  # pragma: no cover - dependency guard
    AIMessage = None
    HumanMessage = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MCP Jose LangChain agent")
    parser.add_argument("prompt", nargs="?", help="Task prompt")
    parser.add_argument(
        "--model", default="gpt-4o-mini", help="OpenAI model for LangChain"
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
        "--interactive", action="store_true", help="Run interactive chat loop"
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

    if args.show_context:
        loader = ProjectContextLoader(repo_root=repo_root)
        print(loader.build_agent_context())
        return 0

    try:
        agent = MCPJoseLangChainAgent(
            repo_root=repo_root,
            model=args.model,
            temperature=args.temperature,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"Failed to initialize LangChain agent: {exc}", file=sys.stderr)
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

    if args.interactive:
        print("Interactive mode. Type 'exit' or 'quit' to stop.")
        chat_history = []
        while True:
            try:
                prompt = input("\nYou> ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if prompt.lower() in {"exit", "quit"}:
                break
            if not prompt:
                continue

            try:
                result = agent.invoke(prompt, chat_history=chat_history)
                output = str(result.get("output", ""))
                print(f"\nAgent> {output}")
                if HumanMessage is not None and AIMessage is not None:
                    chat_history.append(HumanMessage(content=prompt))
                    chat_history.append(AIMessage(content=output))
            except Exception as exc:
                print(f"\nAgent error: {exc}", file=sys.stderr)
        return 0

    if not args.prompt:
        parser.error(
            "prompt is required unless --interactive, --list-tools, --list-skills, or --show-context is used"
        )

    try:
        print(agent.run(args.prompt))
        return 0
    except Exception as exc:
        print(f"Agent execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
