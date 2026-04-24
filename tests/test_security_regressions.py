import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("flask")

from core.config import CredentialManager
from tools.bash_executor import BashExecutor
from tools.payment_webhook import PaymentWebhookTool
from tools.webhook_server import create_webhook_app


@pytest.fixture(autouse=True)
def reset_credential_manager_state():
    CredentialManager._instance = None
    CredentialManager._config = None
    CredentialManager._google_temp_path = None
    yield
    CredentialManager._cleanup_google_temp_file()
    CredentialManager._instance = None
    CredentialManager._config = None
    CredentialManager._google_temp_path = None


def test_mp_webhook_requires_signature_when_secret_configured(tmp_path: Path):
    payload = {"type": "subscription_preapproval", "data": {"id": "sub_123"}}

    with patch("tools.payment_webhook.PaymentWebhookTool") as mock_tool_cls:
        mock_tool = mock_tool_cls.return_value
        mock_tool.creds.get_mercadopago_config.return_value = {"webhook_secret": "secret"}

        app = create_webhook_app(tmp_path / "messages.sqlite")
        response = app.test_client().post("/webhooks/mercadopago", json=payload)

    assert response.status_code == 401
    mock_tool_cls.assert_called_once_with(db_path=str(tmp_path / "messages.sqlite"))
    mock_tool.process_webhook.assert_not_called()


def test_mp_webhook_validates_signature_and_reuses_db_path(tmp_path: Path):
    payload = {"type": "subscription_preapproval", "data": {"id": "sub_456"}}
    headers = {"x-signature": "ts=123,v1=bad-hash", "x-request-id": "req-1"}

    with patch("tools.payment_webhook.PaymentWebhookTool") as mock_tool_cls:
        mock_tool = mock_tool_cls.return_value
        mock_tool.creds.get_mercadopago_config.return_value = {"webhook_secret": "secret"}
        mock_tool.validate_signature.return_value = False

        app = create_webhook_app(tmp_path / "messages.sqlite")
        response = app.test_client().post(
            "/webhooks/mercadopago",
            json=payload,
            headers=headers,
        )

    assert response.status_code == 401
    mock_tool.validate_signature.assert_called_once_with("sub_456", "req-1", "123", "bad-hash")
    mock_tool.process_webhook.assert_not_called()


def test_mp_webhook_processes_verified_events_without_payload_fallbacks(tmp_path: Path):
    payload = {"type": "subscription_preapproval", "data": {"id": "sub_789"}}
    headers = {"x-signature": "ts=456,v1=good-hash", "x-request-id": "req-2"}

    with patch("tools.payment_webhook.PaymentWebhookTool") as mock_tool_cls:
        mock_tool = mock_tool_cls.return_value
        mock_tool.creds.get_mercadopago_config.return_value = {"webhook_secret": "secret"}
        mock_tool.validate_signature.return_value = True
        mock_tool.process_webhook.return_value = {"status": "success", "message": "ok"}

        app = create_webhook_app(tmp_path / "messages.sqlite")
        response = app.test_client().post(
            "/webhooks/mercadopago",
            json=payload,
            headers=headers,
        )

    assert response.status_code == 200
    mock_tool.process_webhook.assert_called_once_with(payload, allow_payload_fallbacks=False)


def test_process_webhook_rejects_unverified_payload_fallbacks(tmp_path: Path):
    tool = PaymentWebhookTool(db_path=str(tmp_path / "accounts.db"))
    payload = {
        "type": "subscription_preapproval",
        "data": {"id": "sub_unverified"},
        "status": "authorized",
        "phone_number": "+573001112233",
        "user_id": "user-1",
    }

    with patch.object(tool, "_fetch_preapproval", return_value=None), patch.object(
        tool,
        "_resolve_phone",
        return_value=None,
    ):
        result = tool.process_webhook(payload, allow_payload_fallbacks=False)

    assert result["status"] == "error"
    with sqlite3.connect(tool.db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    assert count == 0


def test_process_webhook_allows_simulation_payload_fallbacks(tmp_path: Path):
    tool = PaymentWebhookTool(db_path=str(tmp_path / "accounts.db"))
    payload = {
        "type": "subscription_preapproval",
        "data": {"id": "sub_simulated"},
        "status": "authorized",
        "phone_number": "+573009998877",
        "user_id": "user-simulated",
        "plan_id": "plan_simulated",
    }

    with patch.object(tool, "_fetch_preapproval", return_value=None), patch.object(
        tool,
        "_resolve_phone",
        return_value=None,
    ):
        result = tool.process_webhook(payload, allow_payload_fallbacks=True)

    assert result["status"] == "success"
    with sqlite3.connect(tool.db_path) as conn:
        row = conn.execute(
            "SELECT user_id, status, plan_id FROM subscriptions WHERE mp_subscription_id = ?",
            ("sub_simulated",),
        ).fetchone()
    assert row == ("user-simulated", "authorized", "plan_simulated")


def test_bash_executor_runs_commands_via_bash_without_shell_true(tmp_path: Path):
    executor = BashExecutor(allowed_dirs=[str(tmp_path)])
    completed = SimpleNamespace(stdout="HELLO\n", stderr="", returncode=0)

    with patch("tools.bash_executor.subprocess.run", return_value=completed) as mock_run:
        result = executor.execute("printf 'hello' | tr a-z A-Z", cwd=str(tmp_path))

    assert result["ok"] is True
    assert result["stdout"] == "HELLO\n"
    assert mock_run.call_args.args[0] == ["bash", "-lc", "printf 'hello' | tr a-z A-Z"]
    assert mock_run.call_args.kwargs["shell"] is False


def test_bash_executor_preserves_explicit_shell_invocation(tmp_path: Path):
    executor = BashExecutor(allowed_dirs=[str(tmp_path)])
    completed = SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

    with patch("tools.bash_executor.subprocess.run", return_value=completed) as mock_run:
        result = executor.execute("zsh -lc 'echo ok'", cwd=str(tmp_path))

    assert result["ok"] is True
    assert mock_run.call_args.args[0] == ["zsh", "-lc", "echo ok"]
    assert mock_run.call_args.kwargs["shell"] is False


def test_credential_manager_prefers_existing_google_credentials_file(tmp_path: Path):
    existing_creds = tmp_path / "existing-google-creds.json"
    existing_creds.write_text("{}", encoding="utf-8")

    with patch.dict(
        os.environ,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": str(existing_creds),
            "GOOGLE_CREDENTIALS_JSON": '{"type":"service_account"}',
            "GOOGLE_PROJECT_ID": "project-123",
        },
        clear=False,
    ), patch("core.config.tempfile.NamedTemporaryFile") as mock_tempfile:
        config = CredentialManager().get_config()

    assert config.google_credentials_path == existing_creds
    mock_tempfile.assert_not_called()


def test_credential_manager_cleans_up_temp_google_credentials(monkeypatch: pytest.MonkeyPatch):
    registered_callbacks = []

    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", '{"type":"service_account"}')
    monkeypatch.setenv("GOOGLE_PROJECT_ID", "project-456")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    with patch(
        "core.config.atexit.register",
        side_effect=lambda callback: registered_callbacks.append(callback),
    ):
        config = CredentialManager().get_config()

    assert config.google_credentials_path is not None
    assert config.google_credentials_path.exists()
    assert registered_callbacks
    assert oct(config.google_credentials_path.stat().st_mode & 0o777) == "0o600"

    CredentialManager._cleanup_google_temp_file()

    assert not config.google_credentials_path.exists()