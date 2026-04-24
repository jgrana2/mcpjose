"""Core configuration and credential management with singleton pattern."""

import atexit
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Config:
    """Immutable configuration container for all API credentials and settings."""

    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    google_credentials_path: Optional[Path] = None
    google_project_id: Optional[str] = None
    mp_access_token: Optional[str] = None
    mp_public_key: Optional[str] = None
    mp_webhook_secret: Optional[str] = None
    mp_plan_amount: str = "49000"
    mp_currency: str = "COP"
    mp_plan_reason: str = "Premium Tools Subscription"
    mp_back_url: str = "https://mcpjose.com"
    search_backend: str = "ddgs"
    repo_root: Optional[Path] = None

    def __post_init__(self):
        if self.repo_root is None:
            object.__setattr__(self, "repo_root", Path(__file__).resolve().parent.parent)


class CredentialManager:
    _instance: Optional["CredentialManager"] = None
    _config: Optional[Config] = None
    _google_temp_path: Optional[Path] = None

    def __new__(cls) -> "CredentialManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_config(self) -> Config:
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @classmethod
    def _cleanup_google_temp_file(cls) -> None:
        if cls._google_temp_path is None:
            return

        try:
            cls._google_temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        finally:
            cls._google_temp_path = None

    def _load_config(self) -> Config:
        from dotenv import load_dotenv

        repo_root = Path(__file__).resolve().parent.parent
        env_path = repo_root / "auth" / ".env"

        if env_path.exists():
            load_dotenv(env_path)

        google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        google_application_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
        google_creds_path = None

        if google_application_credentials:
            configured_path = Path(google_application_credentials).expanduser()
            if configured_path.is_file():
                google_creds_path = configured_path

        if google_creds_json and google_creds_path is None:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
            tmp.write(google_creds_json)
            tmp.flush()
            tmp.close()
            os.chmod(tmp.name, 0o600)
            type(self)._google_temp_path = Path(tmp.name)
            atexit.register(self._cleanup_google_temp_file)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
            google_creds_path = Path(tmp.name)

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
        key = self.get_config().openai_api_key
        if not key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        return key

    def ensure_google_credentials(self) -> Dict[str, Any]:
        config = self.get_config()
        if not config.google_credentials_path and not os.environ.get("GOOGLE_CREDENTIALS_JSON"):
            raise FileNotFoundError("Google credentials JSON is missing from environment.")
        if not config.google_project_id:
            raise RuntimeError("Google credentials missing GOOGLE_PROJECT_ID")
        return {"project_id": config.google_project_id, "credentials_path": config.google_credentials_path}

    def get_api_key(self, service: str) -> Optional[str]:
        mapping = {"openai": "openai_api_key", "google": "google_api_key", "mercadopago": "mp_access_token"}
        attr = mapping.get(service.lower())
        if attr:
            return getattr(self.get_config(), attr, None)
        return os.environ.get(service.upper())

    def get_mercadopago_config(self) -> Dict[str, Any]:
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


def get_config() -> Config:
    return CredentialManager().get_config()
