"""LangChain agent wired to MCP Jose tools, skills, and AGENTS.md guidance."""

from __future__ import annotations

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

    @staticmethod
    def _build_system_prompt(context_block: str) -> str:
        return (
            "You are MCP Jose's LangChain agent.\n"
            "You MUST use project tools when external actions or data access are needed.\n"
            "Follow AGENTS.md guidance and use project skills when relevant.\n"
            "If a request touches project workflows, call read_agents_md and read_skill.\n"
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
