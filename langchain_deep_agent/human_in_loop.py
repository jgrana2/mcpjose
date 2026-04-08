"""Human-in-the-loop (HITL) configuration for sensitive tool operations.

This module enables approval workflows for sensitive operations like file
deletion, payment processing, or system commands, requiring human review
before execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class InterruptDecision(str, Enum):
    """Possible human decisions for interrupted operations."""

    APPROVE = "approve"  # Execute the operation as requested
    REJECT = "reject"  # Block the operation
    EDIT = "edit"  # Allow editing parameters before execution
    SKIP = "skip"  # Continue without executing


class HumanInTheLoopConfig:
    """Configure human approval requirements for tool operations.

    Deep Agents can interrupt at tool calls requiring human review.
    This configuration specifies which tools need approval and how to handle responses.
    """

    def __init__(self) -> None:
        """Initialize HITL configuration."""
        self.interrupt_config: dict[str, Any] = {}
        self.approval_prompt_template = "Approve this operation? [approve/reject/skip]: "

    def require_approval(
        self,
        tool_name: str,
        allowed_decisions: Optional[list[str]] = None,
    ) -> None:
        """Require human approval for a tool before execution.

        Args:
            tool_name: Name of the tool requiring approval
            allowed_decisions: Allowed responses (e.g., ['approve', 'reject'])
                              If None, defaults to all decisions
        """
        if allowed_decisions:
            self.interrupt_config[tool_name] = {
                "allowed_decisions": allowed_decisions,
            }
        else:
            self.interrupt_config[tool_name] = True

    def no_approval(self, tool_name: str) -> None:
        """Disable approval requirement for a tool.

        Args:
            tool_name: Name of the tool
        """
        if tool_name in self.interrupt_config:
            del self.interrupt_config[tool_name]

    def configure_dangerous_tools(self) -> None:
        """Configure approval for common dangerous operations.

        Includes:
        - File deletion
        - Email sending
        - Payment processing
        - System command execution
        """
        dangerous_tools = {
            "delete_file": ["approve", "reject"],
            "send_email": ["approve", "reject", "edit"],
            "process_payment": ["approve", "reject", "edit"],
            "execute_command": ["approve", "reject"],
            "update_database": ["approve", "reject"],
            "modify_config": ["approve", "reject"],
        }

        for tool_name, allowed_decisions in dangerous_tools.items():
            self.require_approval(tool_name, allowed_decisions)

    def handle_interrupt(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        input_func=None,
    ) -> tuple[InterruptDecision, Optional[dict[str, Any]]]:
        """Handle human interruption for a tool call.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments being passed to the tool
            input_func: Function to get user input (defaults to input())

        Returns:
            Tuple of (decision, edited_args)
            - decision: User's decision (approve/reject/edit/skip)
            - edited_args: Modified arguments if decision is 'edit', else None
        """
        if input_func is None:
            input_func = input

        # Display tool operation for approval
        self._display_tool_operation(tool_name, tool_args)

        # Get allowed decisions for this tool
        tool_config = self.interrupt_config.get(tool_name, {})
        if isinstance(tool_config, dict):
            allowed_decisions = tool_config.get("allowed_decisions", None)
        else:
            allowed_decisions = None

        # Prompt user
        while True:
            try:
                response = input_func(self.approval_prompt_template).strip().lower()

                # Map response to decision
                decision = self._parse_decision(response)

                # Check if decision is allowed
                if allowed_decisions and decision.value not in allowed_decisions:
                    print(f"Decision '{decision.value}' not allowed. Choose from: {','.join(allowed_decisions)}")
                    continue

                if decision == InterruptDecision.EDIT:
                    edited_args = self._prompt_edit_args(tool_args, input_func)
                    return (decision, edited_args)

                return (decision, None)

            except KeyboardInterrupt:
                return (InterruptDecision.SKIP, None)
            except Exception as exc:
                print(f"Error processing decision: {exc}")
                return (InterruptDecision.SKIP, None)

    def _display_tool_operation(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        """Display tool operation details for user review."""
        print(f"\n{'='*60}")
        print(f"⚠️  Tool Approval Required: {tool_name}")
        print(f"{'='*60}")

        if tool_args:
            print("Arguments:")
            for key, value in tool_args.items():
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                print(f"  - {key}: {value_str}")
        else:
            print("(No arguments)")

        print()

    def _parse_decision(self, response: str) -> InterruptDecision:
        """Parse user response to decision enum."""
        response_lower = response.lower().strip()

        decision_map = {
            "a": InterruptDecision.APPROVE,
            "approve": InterruptDecision.APPROVE,
            "yes": InterruptDecision.APPROVE,
            "y": InterruptDecision.APPROVE,
            "r": InterruptDecision.REJECT,
            "reject": InterruptDecision.REJECT,
            "no": InterruptDecision.REJECT,
            "n": InterruptDecision.REJECT,
            "e": InterruptDecision.EDIT,
            "edit": InterruptDecision.EDIT,
            "s": InterruptDecision.SKIP,
            "skip": InterruptDecision.SKIP,
        }

        return decision_map.get(response_lower, InterruptDecision.SKIP)

    def _prompt_edit_args(
        self,
        tool_args: dict[str, Any],
        input_func,
    ) -> dict[str, Any]:
        """Prompt user to edit tool arguments."""
        print("\nEdit Arguments (or press Enter to keep):")

        edited_args = dict(tool_args)

        for key in tool_args:
            current_value = tool_args[key]
            print(f"\n{key} (current: {current_value}): ", end="")

            try:
                new_value = input_func().strip()
                if new_value:
                    # Try to preserve type
                    if isinstance(current_value, bool):
                        edited_args[key] = new_value.lower() in {"true", "yes", "1"}
                    elif isinstance(current_value, (int, float)):
                        try:
                            edited_args[key] = type(current_value)(new_value)
                        except ValueError:
                            edited_args[key] = new_value
                    else:
                        edited_args[key] = new_value
            except KeyboardInterrupt:
                return tool_args

        return edited_args

    def get_interrupt_config(self) -> dict[str, Any]:
        """Get interrupt configuration for create_deep_agent.

        Returns:
            Configuration dictionary ready for Deep Agents
        """
        return {
            "interrupt_on": self.interrupt_config,
            "hitl_enabled": bool(self.interrupt_config),
        }


class OperationApprovalTracker:
    """Track approval history and patterns for auditing."""

    def __init__(self) -> None:
        """Initialize approval tracker."""
        self.approval_history: list[dict[str, Any]] = []

    def record_decision(
        self,
        tool_name: str,
        decision: InterruptDecision,
        tool_args: Optional[dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Record a human approval decision.

        Args:
            tool_name: Tool that was approved/rejected
            decision: Human's decision
            tool_args: Arguments to the tool
            timestamp: Timestamp of decision (auto-generated if None)
        """
        import datetime

        if timestamp is None:
            timestamp = datetime.datetime.now().isoformat()

        self.approval_history.append(
            {
                "timestamp": timestamp,
                "tool": tool_name,
                "decision": decision.value,
                "args_hash": hash(str(tool_args)) if tool_args else None,
            }
        )

    def get_approval_stats(self) -> dict[str, Any]:
        """Get statistics on approval decisions.

        Returns:
            Dictionary with approval statistics and patterns
        """
        if not self.approval_history:
            return {}

        total = len(self.approval_history)
        approved = sum(1 for h in self.approval_history if h["decision"] == "approve")
        rejected = sum(1 for h in self.approval_history if h["decision"] == "reject")
        edited = sum(1 for h in self.approval_history if h["decision"] == "edit")

        # Count by tool
        tool_stats = {}
        for h in self.approval_history:
            tool = h["tool"]
            if tool not in tool_stats:
                tool_stats[tool] = {"approved": 0, "rejected": 0, "edited": 0}
            decision = h["decision"]
            if decision in tool_stats[tool]:
                tool_stats[tool][decision] += 1

        return {
            "total_decisions": total,
            "approved": approved,
            "rejected": rejected,
            "edited": edited,
            "approval_rate": approved / total if total > 0 else 0,
            "by_tool": tool_stats,
            "history": self.approval_history,
        }
