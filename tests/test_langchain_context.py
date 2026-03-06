"""Tests for langchain_agent context loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.context import ProjectContextLoader


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_context_loader_discovers_agents_and_skills(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "# Rules\nAlways validate inputs.")
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
