"""Deep Agents memory, skills, and middleware configuration.

This module provides integration with Deep Agents capabilities:
- Persistent memory stores across conversation threads
- Skills loading and management
- Middleware configuration for custom behaviors
- Long-term context management
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

try:
    from deepagents.backends.utils import create_file_data
except Exception:
    create_file_data = None


class MemoryManager:
    """Manage persistent memory stores for Deep Agents.

    Supports both in-memory and persistent storage backends for maintaining
    conversation context and learned patterns across sessions.
    """

    def __init__(
        self,
        backend_type: str = "memory",
        storage_path: Optional[Path] = None,
    ) -> None:
        """Initialize memory manager.

        Args:
            backend_type: Type of backend ('memory', 'filesystem', 'store')
            storage_path: Path for persistent storage (if applicable)
        """
        self.backend_type = backend_type
        self.storage_path = storage_path or Path(".agent_memory")
        self.memory_files: dict[str, Any] = {}

    def load_agents_md(self, path: Path) -> Optional[str]:
        """Load AGENTS.md file for agent context.

        Args:
            path: Path to AGENTS.md file

        Returns:
            File content as string, or None if not found
        """
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Failed to load AGENTS.md: {exc}")
        return None

    def load_memory_md(self, path: Path) -> Optional[str]:
        """Load MEMORY.md file for persistent preferences.

        Args:
            path: Path to MEMORY.md file

        Returns:
            File content as string, or None if not found
        """
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Failed to load MEMORY.md: {exc}")
        return None

    def prepare_memory_files(
        self,
        agents_md_content: Optional[str] = None,
        memory_md_content: Optional[str] = None,
    ) -> dict[str, Any]:
        """Prepare memory files for Deep Agents configuration.

        Args:
            agents_md_content: Content of AGENTS.md
            memory_md_content: Content of MEMORY.md

        Returns:
            Dictionary of file paths to file data objects
        """
        if create_file_data is None:
            return {}

        files = {}

        if agents_md_content:
            files["/AGENTS.md"] = create_file_data(agents_md_content)

        if memory_md_content:
            files["/MEMORY.md"] = create_file_data(memory_md_content)

        self.memory_files = files
        return files

    def get_memory_config(self) -> dict[str, Any]:
        """Get memory configuration for create_deep_agent.

        Returns:
            Configuration dictionary with memory paths and backend type
        """
        config: dict[str, Any] = {
            "backend_type": self.backend_type,
        }

        if self.backend_type == "filesystem" and self.storage_path:
            config["storage_path"] = str(self.storage_path)

        if self.memory_files:
            config["files"] = self.memory_files

        return config


class SkillsManager:
    """Manage skills loading and configuration for Deep Agents.

    Skills provide specialized knowledge and workflows for domain-specific
    tasks, reducing token usage through progressive disclosure.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize skills manager.

        Args:
            repo_root: Project root directory
        """
        self.repo_root = repo_root
        self.skills_dirs = [
            repo_root / ".agents" / "skills",
            repo_root / "skills",
        ]
        self.loaded_skills: dict[str, dict[str, Any]] = {}

    def discover_skills(self) -> list[dict[str, Any]]:
        """Discover available skills in skills directories.

        Returns:
            List of skill metadata dictionaries
        """
        skills = []

        for skills_dir in self.skills_dirs:
            if not skills_dir.exists():
                continue

            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    try:
                        content = skill_md.read_text(encoding="utf-8")
                        skill_id = skill_dir.name
                        description = self._extract_description(content)
                        skills.append(
                            {
                                "skill_id": skill_id,
                                "path": str(skill_dir),
                                "description": description,
                            }
                        )
                    except Exception as exc:
                        print(f"Failed to load skill {skill_dir.name}: {exc}")

        return skills

    def _extract_description(self, content: str, max_length: int = 150) -> str:
        """Extract description from skill content.

        Args:
            content: Skill markdown content
            max_length: Maximum length of description

        Returns:
            First meaningful line as description
        """
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:max_length]
        return "Skill"

    def load_skill_file(self, skill_path: str, filename: str = "SKILL.md") -> Optional[str]:
        """Load a specific skill file.

        Args:
            skill_path: Path to skill directory
            filename: Filename to load (default: SKILL.md)

        Returns:
            File content as string, or None if not found
        """
        try:
            file_path = Path(skill_path) / filename
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"Failed to load skill file: {exc}")
        return None

    def prepare_skill_files(self, max_skills: int = 10) -> dict[str, Any]:
        """Prepare skill files for Deep Agents configuration.

        Args:
            max_skills: Maximum number of skills to include

        Returns:
            Dictionary of virtual paths to file data objects
        """
        if create_file_data is None:
            return {}

        skills = self.discover_skills()[:max_skills]
        files = {}

        for skill in skills:
            skill_id = skill["skill_id"]
            skill_path = skill["path"]
            skill_md = self.load_skill_file(skill_path)

            if skill_md:
                # Store in virtual filesystem
                virtual_path = f"/skills/{skill_id}/SKILL.md"
                files[virtual_path] = create_file_data(skill_md)
                self.loaded_skills[skill_id] = skill

        return files

    def get_skills_config(self, max_skills: int = 10) -> dict[str, Any]:
        """Get skills configuration for create_deep_agent.

        Args:
            max_skills: Maximum number of skills to load

        Returns:
            Configuration dictionary with skills paths and metadata
        """
        skills = self.discover_skills()[:max_skills]

        return {
            "skills": ["/skills/"],
            "skill_count": len(skills),
            "loaded_skills": self.loaded_skills,
            "available_skills": skills,
        }


class MiddlewareConfig:
    """Configuration for Deep Agents middleware chain.

    Middleware provides custom hooks for tool execution, context management,
    and cross-cutting concerns like logging and error handling.
    """

    def __init__(self) -> None:
        """Initialize middleware configuration."""
        self.middleware_list: list[Any] = []
        self.custom_hooks: dict[str, Any] = {}

    def add_logging_middleware(self, verbose: bool = False) -> None:
        """Add middleware for operation logging.

        Args:
            verbose: Enable verbose logging
        """
        # This would be configured via middleware objects
        self.custom_hooks["logging_enabled"] = verbose

    def add_retry_middleware(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> None:
        """Add middleware for automatic retry with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.custom_hooks["retry_config"] = {
            "max_retries": max_retries,
            "backoff_factor": backoff_factor,
        }

    def add_rate_limiter_middleware(self, requests_per_minute: int = 60) -> None:
        """Add middleware for rate limiting.

        Args:
            requests_per_minute: Rate limit threshold
        """
        self.custom_hooks["rate_limiter"] = {
            "requests_per_minute": requests_per_minute,
        }

    def get_middleware_config(self) -> dict[str, Any]:
        """Get complete middleware configuration.

        Returns:
            Configuration dictionary with middleware settings
        """
        return {
            "middleware_list": self.middleware_list,
            "custom_hooks": self.custom_hooks,
        }
