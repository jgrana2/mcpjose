"""CLI commands for Agentic OS team orchestration.

Usage:
    python cli.py team create --request "Build a Python web API" --team-id my_api_team
    python cli.py team spawn --team-id my_api_team --plan-dir userapp/Plan
    python cli.py team status --team-id my_api_team
    python cli.py team message --team-id my_api_team --to-agent broadcast --message "Status update?"
    python cli.py team shutdown --team-id my_api_team
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse


def add_team_parser(subparsers: Any) -> None:
    """Register team subcommands on the main CLI subparsers."""
    team_parser = subparsers.add_parser(
        "team", help="Agentic OS - Team orchestration commands"
    )
    team_subparsers = team_parser.add_subparsers(
        dest="team_command", help="Team commands"
    )
    team_subparsers.required = True

    # create command - Create a new team from a request or plan
    create_parser = team_subparsers.add_parser(
        "create", help="Create and run a team for a user request"
    )
    create_parser.add_argument(
        "--request",
        required=True,
        help="The user request to fulfill",
    )
    create_parser.add_argument(
        "--team-id",
        default=None,
        help="Team ID (default: auto-generated)",
    )
    create_parser.add_argument(
        "--plan-dir",
        default=None,
        help="Use existing Plan/ directory instead of generating",
    )
    create_parser.add_argument(
        "--max-parallel",
        type=int,
        default=5,
        help="Maximum parallel agents (default: 5)",
    )
    create_parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for team state (default: workflows/{team_id})",
    )
    create_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for team to complete before returning",
    )

    # spawn command - Spawn agents from existing plan
    spawn_parser = team_subparsers.add_parser(
        "spawn", help="Spawn agents from an existing plan directory"
    )
    spawn_parser.add_argument(
        "--team-id",
        required=True,
        help="Team ID",
    )
    spawn_parser.add_argument(
        "--plan-dir",
        required=True,
        help="Path to Plan/ directory with AtomicTasks.json",
    )
    spawn_parser.add_argument(
        "--max-parallel",
        type=int,
        default=5,
        help="Maximum parallel agents (default: 5)",
    )
    spawn_parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for team state",
    )

    # status command - Check team status
    status_parser = team_subparsers.add_parser(
        "status", help="Get team status and progress"
    )
    status_parser.add_argument(
        "team_id",
        help="Team ID to check",
    )
    status_parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for team state",
    )

    # message command - Send message to agent
    message_parser = team_subparsers.add_parser(
        "message", help="Send a message to an agent or broadcast to all"
    )
    message_parser.add_argument(
        "--team-id",
        required=True,
        help="Team ID",
    )
    message_parser.add_argument(
        "--to-agent",
        required=True,
        help="Recipient agent ID (use 'broadcast' for all)",
    )
    message_parser.add_argument(
        "--content",
        required=True,
        help="Message content",
    )
    message_parser.add_argument(
        "--from-agent",
        default="user",
        help="Sender ID (default: user)",
    )
    message_parser.add_argument(
        "--type",
        default="instruction",
        help="Message type (default: instruction)",
    )

    # wait command - Wait for team completion
    wait_parser = team_subparsers.add_parser(
        "wait", help="Wait for all tasks to complete"
    )
    wait_parser.add_argument(
        "team_id",
        help="Team ID to wait for",
    )
    wait_parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between checks (default: 5.0)",
    )
    wait_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait (default: forever)",
    )

    # shutdown command - Shutdown team
    shutdown_parser = team_subparsers.add_parser(
        "shutdown", help="Shutdown all agents in a team"
    )
    shutdown_parser.add_argument(
        "team_id",
        help="Team ID to shutdown",
    )
    shutdown_parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill instead of graceful shutdown",
    )

    # list command - List active teams
    list_parser = team_subparsers.add_parser("list", help="List active teams")
    list_parser.add_argument(
        "--workflows-dir",
        default="workflows",
        help="Directory containing team workflows (default: workflows)",
    )


def handle_team_command(args: Any) -> int:
    """Dispatch team subcommands."""
    if args.team_command == "create":
        return _cmd_create(args)
    if args.team_command == "spawn":
        return _cmd_spawn(args)
    if args.team_command == "status":
        return _cmd_status(args)
    if args.team_command == "message":
        return _cmd_message(args)
    if args.team_command == "wait":
        return _cmd_wait(args)
    if args.team_command == "shutdown":
        return _cmd_shutdown(args)
    if args.team_command == "list":
        return _cmd_list(args)

    print(f"Unknown team command: {args.team_command}", file=sys.stderr)
    return 1


def _cmd_create(args: Any) -> int:
    """Create and run a team for a user request."""
    from datetime import datetime
    from langchain_agent.agent import MCPJoseLangChainAgent

    team_id = args.team_id or f"team_{int(datetime.now().timestamp())}"

    print(f"Creating team '{team_id}' for request: {args.request}")
    print(f"Max parallel agents: {args.max_parallel}")

    try:
        # Create the orchestrator agent
        orchestrator = MCPJoseLangChainAgent()

        # Orchestrate the team
        result = orchestrator.orchestrate_team(
            user_request=args.request,
            team_id=team_id,
            use_plan_dir=args.plan_dir,
            max_parallel=args.max_parallel,
        )

        print(json.dumps(result, indent=2, default=str))

        if args.wait and result.get("team_id"):
            print(f"\nWaiting for team '{result['team_id']}' to complete...")
            from tools.agent_spawner import wait_for_team

            wait_result = wait_for_team(result["team_id"])
            print(json.dumps(wait_result, indent=2, default=str))

        return 0 if result.get("success", True) else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_spawn(args: Any) -> int:
    """Spawn agents from an existing plan."""
    from tools.agent_spawner import spawn_agent_team

    print(f"Spawning team '{args.team_id}' from plan: {args.plan_dir}")

    result = spawn_agent_team(
        team_id=args.team_id,
        plan_dir=args.plan_dir,
        work_dir=args.work_dir,
        max_parallel=args.max_parallel,
    )

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success") else 1


def _cmd_status(args: Any) -> int:
    """Get team status."""
    from tools.agent_spawner import get_team_status

    result = get_team_status(args.team_id, args.work_dir)

    if result.get("success"):
        print(json.dumps(result, indent=2, default=str))
        return 0
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        return 1


def _cmd_message(args: Any) -> int:
    """Send message to agent."""
    from tools.agent_spawner import send_message_to_agent

    result = send_message_to_agent(
        team_id=args.team_id,
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        message_type=args.type,
        content=args.content,
    )

    if result.get("success"):
        print(f"Message sent: {result['message_id']}")
        return 0
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        return 1


def _cmd_wait(args: Any) -> int:
    """Wait for team completion."""
    from tools.agent_spawner import wait_for_team

    print(f"Waiting for team '{args.team_id}'...")

    result = wait_for_team(
        team_id=args.team_id,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )

    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success") else 1


def _cmd_shutdown(args: Any) -> int:
    """Shutdown team."""
    from tools.agent_spawner import shutdown_team

    print(f"Shutting down team '{args.team_id}'...")

    result = shutdown_team(
        team_id=args.team_id,
        graceful=not args.force,
    )

    if result.get("success"):
        print("Team shutdown complete")
        return 0
    else:
        print(f"Error: {result.get('error')}", file=sys.stderr)
        return 1


def _cmd_list(args: Any) -> int:
    """List active teams."""
    workflows_dir = Path(args.workflows_dir)

    if not workflows_dir.exists():
        print("No workflows directory found")
        return 0

    teams = []
    for team_dir in workflows_dir.iterdir():
        if team_dir.is_dir():
            config_file = team_dir / "team_config.json"
            if config_file.exists():
                try:
                    import json

                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        teams.append(
                            {
                                "team_id": config.get("team_id", team_dir.name),
                                "status": config.get("status", "unknown"),
                                "created_at": config.get("created_at"),
                                "total_tasks": config.get("total_tasks", 0),
                            }
                        )
                except (json.JSONDecodeError, IOError):
                    teams.append(
                        {
                            "team_id": team_dir.name,
                            "status": "unknown",
                        }
                    )

    print(json.dumps({"teams": teams, "count": len(teams)}, indent=2, default=str))
    return 0
