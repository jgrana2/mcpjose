"""Claude Code adapter for Agentic OS.

Spawns and manages Claude Code CLI sessions as team members.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.agent_team.adapter import (
    AgentAdapter,
    AgentInstance,
    AgentStatus,
    AgentType,
)


class ClaudeCodeAdapter(AgentAdapter):
    """Adapter for spawning Claude Code CLI sessions.

    Each spawned Claude Code session works on a specific task
    and communicates via shared JSON files.
    """

    def __init__(self, claude_cmd: str = "claude"):
        self.claude_cmd = claude_cmd
        self._check_claude_available()

    def _check_claude_available(self) -> None:
        """Check if Claude Code is installed."""
        try:
            subprocess.run(
                [self.claude_cmd, "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"Claude Code not found. Please install it: {self.claude_cmd}"
            )

    def spawn(
        self,
        agent_id: str,
        role: str,
        task: Dict[str, Any],
        work_dir: Path,
        plan_mode: bool = True,
        timeout_minutes: int = 30,
        subagent_definition: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentInstance:
        """Spawn a Claude Code session for a task.

        Args:
            agent_id: Unique ID for this agent.
            role: Role description (e.g., "tech_lead").
            task: The atomic task to execute.
            work_dir: Directory for outputs.
            plan_mode: If True, require plan approval before changes.
            timeout_minutes: Task timeout.
            subagent_definition: Optional subagent type name to use.
            **kwargs: Additional options.

        Returns:
            AgentInstance for the spawned session.
        """
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Create agent manifest
        manifest = {
            "agent_id": agent_id,
            "role": role,
            "task": task,
            "work_dir": str(work_dir),
            "team_dir": str(work_dir.parent.parent),
            "started_at": datetime.now().isoformat(),
            "timeout_minutes": timeout_minutes,
        }
        manifest_file = work_dir / "agent_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Build the prompt
        task_prompt = self._build_prompt(
            agent_id, role, task, work_dir, subagent_definition
        )

        # Create a runner script
        script_path = work_dir / "run_task.sh"
        output_log = work_dir / "output.log"
        script_content = self._build_script(
            task_prompt, work_dir, output_log, timeout_minutes
        )
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Set environment
        env = os.environ.copy()
        env["AGENT_ID"] = agent_id
        env["AGENT_ROLE"] = role
        env["AGENT_WORK_DIR"] = str(work_dir)

        # Enable agent teams if using experimental feature
        env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

        # Spawn Claude Code
        # Note: Claude Code doesn't have a direct "run" mode like OpenCode
        # We use headless mode with --print for non-interactive execution
        cmd = [
            self.claude_cmd,
            "--prompt",
            task_prompt,
            "--working-dir",
            str(work_dir),
        ]

        # If plan mode is enabled, add appropriate flags
        if plan_mode:
            # Claude Code plan mode - would need specific implementation
            # based on their CLI options
            pass

        with open(output_log, "w", encoding="utf-8") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=work_dir,
                env=env,
            )

        # Create status file
        status_file = work_dir / "status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent_id": agent_id,
                    "status": "running",
                    "pid": process.pid,
                    "started_at": datetime.now().isoformat(),
                },
                f,
            )

        return AgentInstance(
            agent_id=agent_id,
            agent_type=AgentType.CLAUDE_CODE,
            role=role,
            pid=process.pid,
            work_dir=work_dir,
            status=AgentStatus.RUNNING,
            started_at=datetime.now(),
        )

    def _build_prompt(
        self,
        agent_id: str,
        role: str,
        task: Dict[str, Any],
        work_dir: Path,
        subagent_definition: Optional[str],
    ) -> str:
        """Build the task prompt for Claude Code."""
        action = task.get("action", "")
        exact_inputs = task.get("exact_inputs", [])
        exact_outputs = task.get("exact_outputs", [])
        validation_check = task.get("validation_check", "")

        role_instruction = ""
        if subagent_definition:
            role_instruction = (
                f"\nYou are running as the '{subagent_definition}' subagent type."
            )

        prompt = f"""You are an AI team member with the role: {role}{role_instruction}

Your Agent ID: {agent_id}
Work Directory: {work_dir}

## Your Task

{action}

## Inputs
{chr(10).join(f"- {inp}" for inp in exact_inputs) if exact_inputs else "- None specified"}

## Expected Outputs
{chr(10).join(f"- {out}" for out in exact_outputs) if exact_outputs else "- None specified"}

## Validation Check
{validation_check if validation_check else "- Validate outputs match expected format"}

## Team Coordination

You are part of a cross-functional agent team. Coordinate via these shared files:
- Task Board: {work_dir.parent.parent}/task_board.json
- Messages: {work_dir.parent.parent}/messages.json
- Your Output Directory: {work_dir}/

When you complete your task:
1. Save all deliverables to {work_dir}/
2. Write completion status to {work_dir}/status.json with format:
   {{"status": "completed", "outputs": ["file1", "file2"]}}
3. The coordinator will be notified automatically

## Instructions

1. Read and understand the task requirements
2. Check the shared message file for any updates
3. Execute the task to completion
4. Validate your outputs against the validation check
5. Save all outputs to your work directory
6. Mark task as complete by writing status.json

Focus ONLY on this single task. Do not proceed to other tasks.
"""
        return prompt

    def _build_script(
        self,
        task_prompt: str,
        work_dir: Path,
        output_log: Path,
        timeout_minutes: int,
    ) -> str:
        """Build the shell script to run the task."""
        return f"""#!/bin/bash
# Auto-generated Claude Code runner script
set -e

WORK_DIR="{work_dir}"
OUTPUT_LOG="{output_log}"
TIMEOUT={timeout_minutes}

# Change to work directory
cd "$WORK_DIR"

# Run Claude Code with timeout
timeout ${{TIMEOUT}}m claude --prompt "{task_prompt.replace('"', '\\"')}" 2>&1 | tee "$OUTPUT_LOG"

# Mark completion
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo '{{"status": "completed", "exit_code": 0}}' > status.json
elif [ $EXIT_CODE -eq 124 ]; then
    echo '{{"status": "failed", "exit_code": 124, "error": "Timeout after {timeout_minutes} minutes"}}' > status.json
else
    echo '{{"status": "failed", "exit_code": '$EXIT_CODE'}}' > status.json
fi
"""

    def check_status(self, agent: AgentInstance) -> AgentStatus:
        """Check the status of a Claude Code session."""
        if not agent.pid:
            return agent.status

        # Check if process is still running
        try:
            os.kill(agent.pid, 0)
            process_running = True
        except (OSError, ProcessLookupError):
            process_running = False

        # Check status file
        status_file = agent.work_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status_data = json.load(f)
                    file_status = status_data.get("status")

                    if file_status == "completed":
                        return AgentStatus.COMPLETED
                    elif file_status == "failed":
                        agent.error_message = status_data.get("error", "Unknown error")
                        return AgentStatus.FAILED
            except (json.JSONDecodeError, IOError):
                pass

        if not process_running:
            return AgentStatus.FAILED

        return AgentStatus.RUNNING

    def send_message(self, agent: AgentInstance, message: Dict[str, Any]) -> bool:
        """Send a message to a Claude Code agent."""
        inbox_file = agent.work_dir / "inbox.json"

        messages = []
        if inbox_file.exists():
            try:
                with open(inbox_file, "r", encoding="utf-8") as f:
                    messages = json.load(f).get("messages", [])
            except (json.JSONDecodeError, IOError):
                messages = []

        messages.append(
            {
                "timestamp": datetime.now().isoformat(),
                **message,
            }
        )

        with open(inbox_file, "w", encoding="utf-8") as f:
            json.dump({"messages": messages}, f, indent=2)

        return True

    def read_messages(self, agent: AgentInstance) -> list[Dict[str, Any]]:
        """Read messages sent to this agent."""
        inbox_file = agent.work_dir / "inbox.json"
        if not inbox_file.exists():
            return []

        try:
            with open(inbox_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, IOError):
            return []

    def get_output(self, agent: AgentInstance) -> Dict[str, Any]:
        """Get output from a Claude Code session."""
        work_dir = agent.work_dir

        output = {
            "agent_id": agent.agent_id,
            "artifacts": [],
            "logs": "",
        }

        # Read output log
        log_file = work_dir / "output.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    output["logs"] = f.read()
            except IOError:
                pass

        # Collect artifacts
        for item in work_dir.iterdir():
            if item.is_file() and item.name not in (
                "status.json",
                "inbox.json",
                "agent_manifest.json",
            ):
                output["artifacts"].append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size,
                    }
                )

        # Read final status
        status_file = work_dir / "status.json"
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    output["status"] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return output

    def shutdown(self, agent: AgentInstance, graceful: bool = True) -> bool:
        """Shutdown a Claude Code session."""
        if not agent.pid:
            return True

        try:
            if graceful:
                os.kill(agent.pid, 15)  # SIGTERM
                time.sleep(2)

                try:
                    os.kill(agent.pid, 0)
                    os.kill(agent.pid, 9)  # SIGKILL
                except (OSError, ProcessLookupError):
                    pass
            else:
                os.kill(agent.pid, 9)  # SIGKILL

            agent.status = AgentStatus.SHUTDOWN
            return True
        except (OSError, ProcessLookupError):
            return False

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CLAUDE_CODE
