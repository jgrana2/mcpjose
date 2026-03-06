"""Project context loaders for AGENTS.md and local skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

DEFAULT_SKILL_DIRS = (".agents/skills", "skills")


@dataclass(frozen=True)
class SkillDocument:
    """Representation of a skill loaded from SKILL.md."""

    skill_id: str
    name: str
    path: Path
    description: str
    content: str


class ProjectContextLoader:
    """Loads AGENTS.md and all project skills into reusable structures."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        skill_dirs: Optional[Iterable[str]] = None,
    ) -> None:
        self.repo_root = (repo_root or self._infer_repo_root()).resolve()
        self.skill_dirs = tuple(skill_dirs or DEFAULT_SKILL_DIRS)

    @staticmethod
    def _infer_repo_root() -> Path:
        return Path(__file__).resolve().parent.parent

    def agents_path(self) -> Path:
        return self.repo_root / "AGENTS.md"

    def load_agents_guidance(self) -> str:
        """Load AGENTS.md content if available."""
        path = self.agents_path()
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def discover_skill_files(self) -> list[Path]:
        """Return every SKILL.md from configured skill directories."""
        files: list[Path] = []
        for relative_dir in self.skill_dirs:
            base_dir = self.repo_root / relative_dir
            if not base_dir.exists() or not base_dir.is_dir():
                continue
            files.extend(sorted(base_dir.glob("*/SKILL.md")))
        return files

    def load_skills(self) -> Dict[str, SkillDocument]:
        """Load every discovered skill and return a stable identifier map."""
        skills: Dict[str, SkillDocument] = {}
        for skill_path in self.discover_skill_files():
            name = skill_path.parent.name
            skill_id = self._build_skill_id(name=name, path=skill_path, current=skills)
            content = skill_path.read_text(encoding="utf-8")
            description = self._extract_description(content)
            skills[skill_id] = SkillDocument(
                skill_id=skill_id,
                name=name,
                path=skill_path.resolve(),
                description=description or f"Skill guidance for {name}",
                content=content,
            )
        return skills

    def build_agent_context(
        self,
        max_agents_chars: int = 6000,
        max_skill_chars: int = 14000,
        per_skill_chars: int = 700,
    ) -> str:
        """Build prompt-safe context with AGENTS.md plus skill summaries."""
        agents_text = self.load_agents_guidance()
        agents_excerpt = agents_text[:max_agents_chars]

        skills = self.load_skills()
        skill_lines: list[str] = []
        consumed = 0
        for skill in skills.values():
            if consumed >= max_skill_chars:
                break

            excerpt = self._condense(skill.content, per_skill_chars)
            line = (
                f"- {skill.skill_id}: {skill.description}\n"
                f"  Source: {skill.path}\n"
                f"  Excerpt: {excerpt}"
            )
            if consumed + len(line) > max_skill_chars:
                break

            skill_lines.append(line)
            consumed += len(line)

        skill_block = "\n".join(skill_lines) if skill_lines else "No skills discovered."
        return (
            "## AGENTS.md Guidance (excerpt)\n"
            f"{agents_excerpt or 'AGENTS.md was not found.'}\n\n"
            "## Project Skills (catalog + excerpts)\n"
            f"{skill_block}"
        )

    @staticmethod
    def _extract_description(content: str) -> str:
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            return " ".join(line.split())[:240]
        return ""

    @staticmethod
    def _condense(text: str, max_chars: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_chars:
            return compact
        return f"{compact[: max_chars - 3]}..."

    def _build_skill_id(
        self,
        name: str,
        path: Path,
        current: Dict[str, SkillDocument],
    ) -> str:
        if name not in current:
            return name

        parent = path.parent
        relative = parent.relative_to(self.repo_root)
        candidate = str(relative).replace("/", ":")
        if candidate not in current:
            return candidate

        suffix = 2
        while f"{candidate}:{suffix}" in current:
            suffix += 1
        return f"{candidate}:{suffix}"
