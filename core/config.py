"""Core configuration and credential management with singleton pattern."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Config:
    """Immutable configuration container for all API credentials and settings."""

    # OpenAI
    openai_api_key: Optional[str] = None

    # Google
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    google_credentials_path: Optional[Path] = None
    google_project_id: Optional[str] = None

    # Search
    search_backend: str = "ddgs"

    # Paths
    repo_root: Optional[Path] = None

    def __post_init__(self):
        # frozen=True requires object.__setattr__ for post-init modifications
        if self.repo_root is None:
            object.__setattr__(
                self, "repo_root", Path(__file__).resolve().parent.parent
            )


class CredentialManager:
    """Singleton manager for loading and caching credentials from multiple sources.

    Implements the Singleton pattern to ensure credentials are loaded once
    and shared across the application. Follows dependency inversion by
    separating credential loading from tool implementation.
    """

    _instance: Optional["CredentialManager"] = None
    _config: Optional[Config] = None

    def __new__(cls) -> "CredentialManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_config(self) -> Config:
        """Get or initialize the configuration singleton."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Config:
        """Load configuration from JSON files and environment variables.

        Priority: Environment variables > credentials.json > google credentials
        """
        repo_root = Path(__file__).resolve().parent.parent

        # Load main credentials file
        credentials: Dict[str, Any] = {}
        creds_path = repo_root / "auth" / "credentials.json"
        if creds_path.exists():
            with open(creds_path, "r", encoding="utf-8") as f:
                credentials = json.load(f)

        # Set environment variables from credentials (if not already set)
        for key, value in credentials.items():
            if value and key not in os.environ:
                os.environ[key] = str(value)

        # Load Google-specific credentials
        google_creds_path = repo_root / "auth" / "google" / "vision-key.json"
        google_project_id = None
        if google_creds_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(google_creds_path)
            with open(google_creds_path, "r", encoding="utf-8") as f:
                google_creds = json.load(f)
                google_project_id = google_creds.get("project_id")

        return Config(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            google_cse_id=os.environ.get("GOOGLE_CSE_ID"),
            google_credentials_path=google_creds_path
            if google_creds_path.exists()
            else None,
            google_project_id=google_project_id or os.environ.get("GOOGLE_PROJECT_ID"),
            search_backend=os.environ.get("SEARCH_ENGINE", "ddgs").lower(),
            repo_root=repo_root,
        )

    def ensure_openai_key(self) -> str:
        """Validate and return OpenAI API key.

        Raises:
            EnvironmentError: If OPENAI_API_KEY is not configured.
        """
        key = self.get_config().openai_api_key
        if not key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        return key

    def ensure_google_credentials(self) -> Dict[str, Any]:
        """Validate and return Google credentials.

        Raises:
            FileNotFoundError: If Google credentials file is missing.
            RuntimeError: If project_id is not found in credentials.
        """
        config = self.get_config()
        if (
            not config.google_credentials_path
            or not config.google_credentials_path.exists()
        ):
            raise FileNotFoundError(
                f"Google credentials not found at {config.google_credentials_path}"
            )

        if not config.google_project_id:
            raise RuntimeError("Google credentials missing project_id")

        return {
            "project_id": config.google_project_id,
            "credentials_path": config.google_credentials_path,
        }


# Global accessor for convenience
def get_config() -> Config:
    """Get the global configuration singleton."""
    return CredentialManager().get_config()
