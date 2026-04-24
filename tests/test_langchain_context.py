"""Tests for langchain_agent context loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.agent import MCPJoseLangChainAgent
from langchain_agent.context import ProjectContextLoader
from langchain_agent.tool_registry import ProjectToolRegistry


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_context_loader_discovers_agents_and_skills(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "# Rules\nAlways validate inputs.")
    _write(
        tmp_path / "MEMORY.md",
        "# Memory\nStore durable preferences.\nDo not store secrets.",
    )
    _write(
        tmp_path / ".agents" / "skills" / "alpha" / "SKILL.md",
        "# Alpha\nAlpha description\nAlpha details.",
    )
    _write(
        tmp_path / "skills" / "beta" / "SKILL.md",
        "# Beta\nBeta description\nBeta details.",
    )

    loader = ProjectContextLoader(repo_root=tmp_path)

    agents = loader.load_agents_guidance()
    skills = loader.load_skills()
    context = loader.build_agent_context()

    assert "Always validate inputs." in agents
    assert "alpha" in skills
    assert "beta" in skills
    assert "AGENTS.md Guidance" in context
    assert "Project Skills" in context
    assert "alpha" in context
    assert "beta" in context
    assert "MEMORY.md Guidance" in context
    assert "Store durable preferences." in context


def test_context_loader_handles_duplicate_skill_names(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agents" / "skills" / "shared" / "SKILL.md",
        "# Shared\nFirst shared skill.",
    )
    _write(
        tmp_path / "skills" / "shared" / "SKILL.md",
        "# Shared\nSecond shared skill.",
    )

    loader = ProjectContextLoader(repo_root=tmp_path)
    skills = loader.load_skills()

    assert len(skills) == 2
    assert "shared" in skills
    assert "skills:shared" in skills


def test_system_prompt_instructs_automatic_tool_use() -> None:
    prompt = MCPJoseLangChainAgent._build_system_prompt("CTX")

    assert "Do not tell the user you lack access if a safe tool can retrieve the answer." in prompt
    assert "Current time, date, timezone, shell environment, or repo state" in prompt
    assert "list_skills first, then read_skill" in prompt


def test_tool_registry_describes_bash_for_environment_queries(tmp_path: Path) -> None:
    registry = ProjectToolRegistry(repo_root=tmp_path)

    specs = {name: description for name, description, _func in registry.tool_specs()}

    assert "bash_execute" in specs
    assert "current time/date" in specs["bash_execute"]
    assert "read-only environment and repository inspection" in specs["bash_execute"]
