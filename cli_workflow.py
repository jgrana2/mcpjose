"""Workflow CLI commands.

Extends the existing CLI pattern in cli.py without modifying it directly.
Called via add_workflow_parser() / handle_workflow_command() from cli.py.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def add_workflow_parser(subparsers: Any) -> None:
    """Register workflow subcommands on the main CLI subparsers.

    Args:
        subparsers: argparse _SubParsersAction from build_parser().
    """
    workflow_parser = subparsers.add_parser(
        "workflow", help="Workflow orchestration commands"
    )
    workflow_subparsers = workflow_parser.add_subparsers(
        dest="workflow_command", help="Workflow commands"
    )
    workflow_subparsers.required = True

    # execute command
    execute_parser = workflow_subparsers.add_parser(
        "execute", help="Execute a workflow from a plan directory"
    )
    execute_parser.add_argument(
        "plan_dir",
        help="Path to plan directory containing AtomicTasks.json",
    )
    execute_parser.add_argument(
        "--workflow-id",
        default=None,
        dest="workflow_id",
        help="Workflow ID (default: workflow_<timestamp>)",
    )
    execute_parser.add_argument(
        "--state-dir",
        default="workflows",
        dest="state_dir",
        help="Directory for workflow state files (default: workflows/)",
    )

    # status command
    status_parser = workflow_subparsers.add_parser(
        "status", help="Show status of a workflow"
    )
    status_parser.add_argument("workflow_id", help="Workflow ID to inspect")
    status_parser.add_argument(
        "--state-dir",
        default="workflows",
        dest="state_dir",
        help="Directory for workflow state files (default: workflows/)",
    )

    # list command
    list_parser = workflow_subparsers.add_parser(
        "list", help="List all tracked workflows"
    )
    list_parser.add_argument(
        "--state-dir",
        default="workflows",
        dest="state_dir",
        help="Directory for workflow state files (default: workflows/)",
    )


def handle_workflow_command(args: Any) -> int:
    """Dispatch workflow subcommands.

    Args:
        args: Parsed argparse namespace.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    if args.workflow_command == "execute":
        return _cmd_execute(args)
    if args.workflow_command == "status":
        return _cmd_status(args)
    if args.workflow_command == "list":
        return _cmd_list(args)
    print(f"Unknown workflow command: {args.workflow_command}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def _cmd_execute(args: Any) -> int:
    """Execute workflow command."""
    from mcp_server.workflow_executor import BasicWorkflowExecutor

    plan_dir = Path(args.plan_dir)
    atomic_tasks_path = plan_dir / "AtomicTasks.json"
    if not atomic_tasks_path.exists():
        print(
            f"Error: AtomicTasks.json not found in {plan_dir}",
            file=sys.stderr,
        )
        return 1

    workflow_id = args.workflow_id or f"workflow_{int(datetime.now().timestamp())}"
    state_dir = Path(args.state_dir)

    print(f"Starting workflow '{workflow_id}' from {plan_dir} ...")

    executor = BasicWorkflowExecutor(state_dir=state_dir)
    result = executor.execute_workflow(workflow_id, plan_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


def _cmd_status(args: Any) -> int:
    """Show workflow status command."""
    from core.workflow_state import WorkflowStateManager

    state_manager = WorkflowStateManager(Path(args.state_dir))
    state = state_manager.load_state(args.workflow_id)

    if not state:
        print(f"Workflow '{args.workflow_id}' not found.", file=sys.stderr)
        return 1

    print(json.dumps(state, indent=2, ensure_ascii=False, default=str))
    return 0


def _cmd_list(args: Any) -> int:
    """List workflows command."""
    from core.workflow_state import WorkflowStateManager

    state_manager = WorkflowStateManager(Path(args.state_dir))
    workflows = state_manager.list_workflows()

    if not workflows:
        print("No workflows found.")
        return 0

    print(json.dumps(workflows, indent=2, ensure_ascii=False, default=str))
    return 0
