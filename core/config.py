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

    # MercadoPago
    mp_access_token: Optional[str] = None
    mp_public_key: Optional[str] = None
    mp_webhook_secret: Optional[str] = None
    mp_plan_amount: str = "49000"
    mp_currency: str = "COP"
    mp_plan_reason: str = "Premium Tools Subscription"
    mp_back_url: str = "https://mcpjose.com"

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
        """Load configuration strictly from environment variables natively."""
        from dotenv import load_dotenv

        repo_root = Path(__file__).resolve().parent.parent
        env_path = repo_root / "auth" / ".env"

        if env_path.exists():
            load_dotenv(env_path)

        # Handle the bundled JSON credential string as a temp environment file for Vision natively
        google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
        google_creds_path = None

        if google_creds_json:
            import tempfile

            # Write a temporary credential file for SDK usage securely
            fd, temp_path = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, 'w') as f:
                f.write(google_creds_json)

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
            google_creds_path = Path(temp_path)

        return Config(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            google_cse_id=os.environ.get("GOOGLE_CSE_ID"),
            google_credentials_path=google_creds_path,
            google_project_id=google_project_id,
            search_backend=os.environ.get("SEARCH_ENGINE", "ddgs").lower(),
            mp_access_token=os.environ.get("MP_ACCESS_TOKEN"),
            mp_public_key=os.environ.get("MP_PUBLIC_KEY"),
            mp_webhook_secret=os.environ.get("MP_WEBHOOK_SECRET"),
            mp_plan_amount=os.environ.get("MP_PLAN_AMOUNT", "49000"),
            mp_currency=os.environ.get("MP_CURRENCY", "COP"),
            mp_plan_reason=os.environ.get("MP_PLAN_REASON", "Premium Tools Subscription"),
            mp_back_url=os.environ.get("MP_BACK_URL", "https://mcpjose.com"),
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
        """Validate and return Google credentials."""
        config = self.get_config()
        # Fallback to check if GOOGLE_CREDENTIALS_JSON is in environment
        if not config.google_credentials_path and not os.environ.get("GOOGLE_CREDENTIALS_JSON"):
            raise FileNotFoundError("Google credentials JSON is missing from environment.")

        if not config.google_project_id:
            raise RuntimeError("Google credentials missing GOOGLE_PROJECT_ID")

        return {
            "project_id": config.google_project_id,
            "credentials_path": config.google_credentials_path,
        }

    def get_api_key(self, service: str) -> Optional[str]:
        """Generic API key lookup by service name.

        Supports: 'openai', 'google', 'mercadopago'
        """
        mapping = {
            "openai": "openai_api_key",
            "google": "google_api_key",
            "mercadopago": "mp_access_token",
        }
        attr = mapping.get(service.lower())
        if attr:
            return getattr(self.get_config(), attr, None)
        return os.environ.get(service.upper())

    def get_mercadopago_config(self) -> Dict[str, Any]:
        """Return all MercadoPago configuration values."""
        cfg = self.get_config()
        return {
            "access_token": cfg.mp_access_token,
            "public_key": cfg.mp_public_key,
            "webhook_secret": cfg.mp_webhook_secret,
            "plan_amount": float(cfg.mp_plan_amount or "0"),
            "currency": cfg.mp_currency,
            "plan_reason": cfg.mp_plan_reason,
            "back_url": cfg.mp_back_url,
        }


# Global accessor for convenience
def get_config() -> Config:
    """Get the global configuration singleton."""
    return CredentialManager().get_config()
