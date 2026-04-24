"""LangChain agent wired to MCP Jose tools, skills, and AGENTS.md guidance."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .context import ProjectContextLoader
from .tool_registry import ProjectToolRegistry

_IMPORT_ERRORS: list[str] = []

try:
    from langchain_openai import ChatOpenAI
except Exception as exc:  # pragma: no cover - dependency guard
    ChatOpenAI = None  # type: ignore[assignment]
    _IMPORT_ERRORS.append(f"langchain_openai.ChatOpenAI import failed: {exc!r}")

try:
    from langchain_core.messages import BaseMessage
except Exception as exc:  # pragma: no cover - dependency guard
    BaseMessage = Any  # type: ignore[assignment]
    _IMPORT_ERRORS.append(f"langchain_core.messages import failed: {exc!r}")

# LangChain v1 API
try:
    from langchain.agents import create_agent as create_agent_v1
except Exception as exc:  # pragma: no cover - dependency guard
    create_agent_v1 = None
    _IMPORT_ERRORS.append(f"langchain.agents.create_agent import failed: {exc!r}")

# Legacy LangChain API
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
except Exception as exc:  # pragma: no cover - dependency guard
    AgentExecutor = Any  # type: ignore[assignment]
    ChatPromptTemplate = Any  # type: ignore[assignment]
    MessagesPlaceholder = Any  # type: ignore[assignment]
    create_tool_calling_agent = None
    _IMPORT_ERRORS.append(
        f"legacy agent imports (AgentExecutor/create_tool_calling_agent) failed: {exc!r}"
    )

_LANGCHAIN_IMPORT_ERROR: Optional[str] = None
if ChatOpenAI is None or (
    create_agent_v1 is None and create_tool_calling_agent is None
):
    _LANGCHAIN_IMPORT_ERROR = " | ".join(_IMPORT_ERRORS)


class MCPJoseLangChainAgent:
    """Runnable LangChain agent for this repository."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        model: str = "gpt-5.4-mini",
        temperature: float = 0.0,
        max_iterations: int = 12,
        verbose: bool = False,
    ) -> None:
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise RuntimeError(
                "LangChain runtime is not available. "
                f"Import details: {_LANGCHAIN_IMPORT_ERROR}"
            )

        self.repo_root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
        self._load_project_env()

        self.context_loader = ProjectContextLoader(self.repo_root)
        self.tool_registry = ProjectToolRegistry(
            repo_root=self.repo_root,
            context_loader=self.context_loader,
        )
        self.tools = self.tool_registry.as_langchain_tools()

        context_block = self.context_loader.build_agent_context()
        self.system_prompt = self._build_system_prompt(context_block)
        llm = ChatOpenAI(model=model, temperature=temperature)

        if create_agent_v1 is not None:
            self._runtime = "v1"
            self.graph = create_agent_v1(
                model=llm,
                tools=self.tools,
                system_prompt=self.system_prompt,
                debug=verbose,
            )
            self.executor = None
        else:
            self._runtime = "legacy"
            prompt = self._build_legacy_prompt(self.system_prompt)
            runnable_agent = create_tool_calling_agent(
                llm=llm, tools=self.tools, prompt=prompt
            )
            self.executor = AgentExecutor(
                agent=runnable_agent,
                tools=self.tools,
                max_iterations=max_iterations,
                verbose=verbose,
                handle_parsing_errors=True,
            )
            self.graph = None

    def invoke(
        self,
        user_input: str,
        chat_history: Optional[list[BaseMessage]] = None,
    ) -> Dict[str, Any]:
        """Run one agent turn and return full result payload."""
        if self._runtime == "v1":
            messages: list[Any] = []
            if chat_history:
                messages.extend(chat_history)
            messages.append({"role": "user", "content": user_input})

            result = self.graph.invoke({"messages": messages})
            output = self._extract_output_text(result)
            if isinstance(result, dict):
                response = dict(result)
                response["output"] = output
                return response
            return {"output": output, "result": result}

        payload = {"input": user_input, "chat_history": chat_history or []}
        return self.executor.invoke(payload)

    def run(
        self, user_input: str, chat_history: Optional[list[BaseMessage]] = None
    ) -> str:
        """Run one turn and return only the assistant output string."""
        result = self.invoke(user_input=user_input, chat_history=chat_history)
        return str(result.get("output", ""))

    def list_tool_names(self) -> list[str]:
        """Return available tool names."""
        return [tool.name for tool in self.tools]

    def list_skills(self) -> Dict[str, Any]:
        """Return discovered skills metadata."""
        return self.tool_registry.list_skills()

    def orchestrate_team(
        self,
        user_request: str,
        team_id: Optional[str] = None,
        use_plan_dir: Optional[str] = None,
        max_parallel: int = 5,
    ) -> Dict[str, Any]:
        """Orchestrate a cross-functional agent team to execute a request.

        This is the main entry point for Agentic OS team execution. It can either:
        1. Load an existing plan from use_plan_dir
        2. Generate a plan dynamically using DECOMPOSITION.md

        Args:
            user_request: The user's request to fulfill.
            team_id: Unique identifier for this team (generated if not provided).
            use_plan_dir: Optional path to existing Plan/ directory.
            max_parallel: Maximum agents to run in parallel.

        Returns:
            Dictionary with execution results.
        """
        from core.agent_team import AgentTeamCoordinator
        from tools.agent_spawner import (
            spawn_agent_team,
            wait_for_team,
        )

        team_id = team_id or f"team_{int(datetime.now().timestamp())}"

        if use_plan_dir:
            # Use existing plan
            result = spawn_agent_team(
                team_id=team_id,
                plan_dir=use_plan_dir,
                max_parallel=max_parallel,
            )
        else:
            # Generate plan dynamically using DECOMPOSITION skill
            plan = self._generate_decomposition_plan(user_request)

            # Create coordinator with dynamic plan
            from pathlib import Path
            from tools.agent_spawner.langchain_adapter import LangChainSubagentAdapter

            coordinator = AgentTeamCoordinator(team_id, Path(f"workflows/{team_id}"))

            # Register adapters
            coordinator.register_adapter(LangChainSubagentAdapter())

            coordinator.create_dynamic_plan(user_request, plan["atomic_tasks"])

            # Spawn agents for each task
            spawned = []
            for task in plan["atomic_tasks"][:max_parallel]:
                role = self._determine_role(
                    task["action"], task.get("tool_or_endpoint", "")
                )
                agent_type = self._select_agent_type(task)

                try:
                    agent = coordinator.spawn_agent(agent_type, role, task["task_id"])
                    spawned.append(
                        {
                            "agent_id": agent.agent_id,
                            "role": role,
                            "task_id": task["task_id"],
                        }
                    )
                except Exception as e:
                    spawned.append(
                        {
                            "task_id": task["task_id"],
                            "error": str(e),
                        }
                    )

            result = {
                "success": True,
                "team_id": team_id,
                "spawned_agents": spawned,
            }

        if not result.get("success"):
            return result

        # Wait for completion
        wait_result = wait_for_team(team_id)

        return {
            "team_id": team_id,
            "plan_result": result,
            "execution_result": wait_result,
        }

    def _generate_decomposition_plan(self, user_request: str) -> Dict[str, Any]:
        """Generate a plan using DECOMPOSITION.md framework."""
        # Use call_llm to generate the plan
        decomposition_prompt = f"""You are a task decomposition specialist.

Read the DECOMPOSITION.md framework and generate a complete plan for this request:

USER REQUEST:
{user_request}

Generate:
1. A task tree with hierarchical IDs (1, 1.1, 1.1.1, etc.)
2. Atomic tasks for all leaf nodes

Return a JSON object with:
{{
    "reasoning": "Brief reasoning chain",
    "task_tree": [...],
    "atomic_tasks": [
        {{
            "task_id": "1.1.1",
            "parent_id": "1.1",
            "depth": 2,
            "action": "Description of what to do",
            "exact_inputs": [...],
            "exact_outputs": [...],
            "tool_or_endpoint": "Tool to use",
            "validation_check": "How to validate",
            "dependencies": [...]
        }}
    ]
}}
"""

        # Use the registry to call LLM
        response = self.tool_registry.call_llm({"prompt": decomposition_prompt})

        # Parse the JSON from response
        import json
        import re

        text = response.get("text", "")

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)

        try:
            plan = json.loads(text)
            return plan
        except json.JSONDecodeError:
            # Return a simple fallback plan
            return {
                "atomic_tasks": [
                    {
                        "task_id": "1.1",
                        "parent_id": "1",
                        "depth": 1,
                        "action": user_request,
                        "exact_inputs": [],
                        "exact_outputs": ["result"],
                        "tool_or_endpoint": "call_llm",
                        "validation_check": "Output is present",
                        "dependencies": [],
                    }
                ]
            }

    def _determine_role(self, action: str, tool_or_endpoint: str) -> str:
        """Determine agent role based on task."""
        action_lower = action.lower()

        if any(w in action_lower for w in ["business", "requirements", "stakeholder"]):
            return "business_analyst"
        if any(w in action_lower for w in ["code", "implement", "develop", "refactor"]):
            return "tech_lead"
        if any(w in action_lower for w in ["test", "qa", "validate", "verify"]):
            return "qa_engineer"
        if any(w in action_lower for w in ["deploy", "infra", "pipeline", "devops"]):
            return "devops_engineer"
        if any(w in action_lower for w in ["research", "investigate", "explore"]):
            return "researcher"
        if any(w in action_lower for w in ["design", "ux", "ui", "interface"]):
            return "ux_designer"

        return "generalist"

    def _select_agent_type(self, task: Dict[str, Any]):
        """Select appropriate agent type for a task."""
        from core.agent_team.adapter import AgentType

        action = task.get("action", "").lower()

        # Complex development tasks -> External agents
        if any(w in action for w in ["implement", "refactor", "code review", "build"]):
            # Prefer OpenCode for coding tasks
            try:
                from tools.agent_spawner.opencode_adapter import OpenCodeAdapter

                OpenCodeAdapter()
                return AgentType.OPENCODE
            except RuntimeError:
                pass

            try:
                from tools.agent_spawner.claude_code_adapter import ClaudeCodeAdapter

                ClaudeCodeAdapter()
                return AgentType.CLAUDE_CODE
            except RuntimeError:
                pass

        # Default to in-process LangChain subagent
        return AgentType.LANGCHAIN_SUBAGENT

    @staticmethod
    def _build_system_prompt(context_block: str) -> str:
        return (
            "You are MCP Jose's LangChain agent - an Agentic OS orchestrator.\n"
            "You MUST use project tools whenever they can answer a request more accurately than model knowledge.\n"
            "Do not tell the user you lack access if a safe tool can retrieve the answer.\n"
            "For local machine, repository, filesystem, time, date, or environment facts, prefer tool calls over assumptions.\n"
            "Examples:\n"
            "- Current time, date, timezone, shell environment, or repo state: use bash_execute with a read-only command.\n"
            "- Current directory, files, or file contents: use filesystem tools.\n"
            "- Project instructions and conventions: use read_agents_md.\n"
            "- Domain-specific workflows or templates: use list_skills first, then read_skill when relevant.\n"
            "Follow AGENTS.md guidance and use project skills when relevant.\n"
            "Consult MEMORY.md guidance for persistent preferences, prior decisions, and project conventions.\n"
            "Use query_memory to recover relevant past context and save_memory to persist useful summaries.\n"
            "If a request touches project workflows, call read_agents_md, list_skills, and read_skill.\n\n"
            "## Agent Team Orchestration (Agentic OS)\n"
            "You can orchestrate cross-functional agent teams for complex tasks:\n"
            "- Use `spawn_agent` to spawn individual agents (opencode, claude_code, langchain_subagent)\n"
            "- Use `spawn_agent_team` to spawn a complete team from a Plan/ directory\n"
            "- Use `get_team_status` to check progress\n"
            "- Use `send_message_to_agent` to communicate with team members\n"
            "- Use `wait_for_team` to wait for completion\n"
            "- Use `shutdown_team` to gracefully stop all agents\n"
            "- Use `orchestrate_team()` method for full end-to-end orchestration\n\n"
            "## Legacy Delegation\n"
            "You can also delegate to predefined internal agents using `delegate_to_agent`.\n"
            "Predefined agent names: basic_workflow_executor.\n\n"
            "Always prefer factual tool outputs over assumptions.\n\n"
            f"{context_block}"
        )

    @staticmethod
    def _build_legacy_prompt(system_prompt: str) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def _load_project_env(self) -> None:
        env_path = self.repo_root / "auth" / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    def _extract_output_text(self, result: Any) -> str:
        if not isinstance(result, dict):
            return str(result)

        messages = result.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                msg_type = getattr(message, "type", None)
                role = getattr(message, "role", None)
                if msg_type in {"ai", "assistant"} or role == "assistant":
                    return self._message_content_to_text(
                        getattr(message, "content", "")
                    )

                if isinstance(message, dict) and message.get("role") == "assistant":
                    return self._message_content_to_text(message.get("content", ""))

        if "output" in result:
            return str(result["output"])
        return str(result)

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(part for part in parts if part)
        return str(content)
