"""LangChain subagent adapter for Agentic OS.

Runs subagents in-process within the orchestrator's Python process.
Useful for lightweight tasks that don't need full OC/CC sessions.
"""

from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.agent_team.adapter import (
    AgentAdapter,
    AgentInstance,
    AgentStatus,
    AgentType,
)


class LangChainSubagentAdapter(AgentAdapter):
    """Adapter for running LangChain subagents in-process.

    These are lightweight agents that run within the orchestrator process,
    suitable for simple tasks that don't require a full OC/CC session.
    """

    def __init__(self, agent_factory: Optional[Callable] = None):
        """Initialize with an optional agent factory.

        Args:
            agent_factory: Callable that returns a LangChain agent instance.
                          If None, uses basic tool execution.
        """
        self.agent_factory = agent_factory
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._results: Dict[str, Any] = {}

    def spawn(
        self,
        agent_id: str,
        role: str,
        task: Dict[str, Any],
        work_dir: Path,
        **kwargs: Any,
    ) -> AgentInstance:
        """Spawn an in-process LangChain subagent.

        Actually starts a thread that executes the task.
        """
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        # Save task manifest
        manifest = {
            "agent_id": agent_id,
            "role": role,
            "task": task,
            "work_dir": str(work_dir),
            "started_at": datetime.now().isoformat(),
        }
        manifest_file = work_dir / "agent_manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Create status file
        status_file = work_dir / "status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent_id": agent_id,
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                },
                f,
            )

        # Start task in thread
        thread = threading.Thread(
            target=self._execute_task,
            args=(agent_id, role, task, work_dir),
            daemon=True,
        )
        self._running_tasks[agent_id] = thread
        thread.start()

        return AgentInstance(
            agent_id=agent_id,
            agent_type=AgentType.LANGCHAIN_SUBAGENT,
            role=role,
            pid=None,  # In-process, no separate PID
            work_dir=work_dir,
            status=AgentStatus.RUNNING,
            started_at=datetime.now(),
        )

    def _execute_task(
        self,
        agent_id: str,
        role: str,
        task: Dict[str, Any],
        work_dir: Path,
    ) -> None:
        """Execute the task in a background thread."""
        try:
            action = task.get("action", "")

            # Simple implementation: execute as tool calls
            # More advanced: use actual LangChain agent
            if self.agent_factory:
                agent = self.agent_factory()
                result = agent.run(action)
            else:
                # Basic execution using tool registry
                result = self._execute_with_tools(task)

            # Save result
            self._results[agent_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat(),
            }

            # Write status file
            status_file = work_dir / "status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "agent_id": agent_id,
                        "status": "completed",
                        "completed_at": datetime.now().isoformat(),
                    },
                    f,
                )

            # Save output
            output_file = work_dir / "output.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)

        except Exception as e:
            error_msg = str(e)
            traceback_str = traceback.format_exc()

            self._results[agent_id] = {
                "status": "failed",
                "error": error_msg,
                "traceback": traceback_str,
            }

            status_file = work_dir / "status.json"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "agent_id": agent_id,
                        "status": "failed",
                        "error": error_msg,
                        "completed_at": datetime.now().isoformat(),
                    },
                    f,
                )

            # Write error log
            log_file = work_dir / "error.log"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(traceback_str)

        finally:
            if agent_id in self._running_tasks:
                del self._running_tasks[agent_id]

    def _execute_with_tools(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using the ProjectToolRegistry."""
        from langchain_agent.tool_registry import ProjectToolRegistry

        registry = ProjectToolRegistry()

        # Map task to tool
        tool_name = self._map_task_to_tool(task)
        arguments = self._prepare_arguments(task)

        try:
            result = registry.call_tool(tool_name, arguments)
            return {"success": True, "tool": tool_name, "result": result}
        except Exception as e:
            return {"success": False, "tool": tool_name, "error": str(e)}

    def _map_task_to_tool(self, task: Dict[str, Any]) -> str:
        """Map task action to tool name."""
        action = task.get("action", "").lower()
        tool_hint = task.get("tool_or_endpoint", "").lower()

        # Keyword mappings
        if "search" in action or "search" in tool_hint:
            return "search"
        if "read" in action or "file" in tool_hint:
            return "read_file"
        if "write" in action or "save" in tool_hint:
            return "write_file"
        if "navigate" in action or "url" in tool_hint:
            return "navigate_to_url"
        if "llm" in action or "generate" in action:
            return "call_llm"
        if "bash" in action or "run" in action or "execute" in action:
            return "bash_execute"

        return "call_llm"  # Default to LLM

    def _prepare_arguments(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare tool arguments from task."""
        action = task.get("action", "")
        exact_inputs = task.get("exact_inputs", [])

        # Extract file paths
        file_paths = [
            inp.replace("path:", "").strip()
            for inp in exact_inputs
            if inp.startswith("path:")
        ]

        tool_name = self._map_task_to_tool(task)

        if tool_name == "read_file" and file_paths:
            return {"path": file_paths[0]}
        if tool_name == "bash_execute":
            return {"command": action}
        if tool_name in ("call_llm", "search"):
            return {"prompt": action, "query": action}

        return {"command": action}

    def check_status(self, agent: AgentInstance) -> AgentStatus:
        """Check the status of a subagent."""
        agent_id = agent.agent_id

        # Check thread status
        if agent_id in self._running_tasks:
            thread = self._running_tasks[agent_id]
            if thread.is_alive():
                return AgentStatus.RUNNING

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
                        return AgentStatus.FAILED
            except (json.JSONDecodeError, IOError):
                pass

        # If thread not running and no status file, assume completed
        return AgentStatus.COMPLETED

    def send_message(self, agent: AgentInstance, message: Dict[str, Any]) -> bool:
        """Send a message to a subagent.

        For in-process agents, messages go to inbox file.
        """
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
        """Read messages for this subagent."""
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
        """Get output from a subagent."""
        work_dir = agent.work_dir
        output = {
            "agent_id": agent.agent_id,
            "artifacts": [],
        }

        # Get cached result if available
        if agent.agent_id in self._results:
            output["result"] = self._results[agent.agent_id]

        # Read output file
        output_file = work_dir / "output.json"
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    output["output"] = json.load(f)
            except (json.JSONDecodeError, IOError):
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

        return output

    def shutdown(self, agent: AgentInstance, graceful: bool = True) -> bool:
        """Shutdown a subagent.

        For threads, we can't really force shutdown, so we just mark it.
        """
        agent_id = agent.agent_id

        if agent_id in self._running_tasks:
            # Can't force stop a thread, just wait
            thread = self._running_tasks[agent_id]
            if thread.is_alive():
                thread.join(timeout=5.0)

        agent.status = AgentStatus.SHUTDOWN
        return True

    @property
    def agent_type(self) -> AgentType:
        return AgentType.LANGCHAIN_SUBAGENT
