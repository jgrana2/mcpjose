import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.payment_gateway import PaymentGatewayTool


@pytest.fixture
def payment_gateway():
    with patch("core.config.CredentialManager") as MockCreds:
        creds_instance = MockCreds.return_value
        creds_instance.get_api_key.return_value = "APP_USR-test-token"
        creds_instance.get_mercadopago_config.return_value = {
            "access_token": "APP_USR-test-token",
            "plan_amount": 999.0,
            "currency": "ARS",
            "plan_reason": "Premium",
            "back_url": "https://example.com/return",
            "payer_email": "tester@example.com",
            "webhook_secret": "",
        }

        pg = PaymentGatewayTool(db_path=":memory:")
        pg.creds = creds_instance
        return pg


def test_get_subscription_success(payment_gateway):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "authorized", "id": "preapproval_123"}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        result = payment_gateway._mp_get("/preapproval/preapproval_123")

    assert result == {"status": "authorized", "id": "preapproval_123"}


def test_create_checkout_link(payment_gateway):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "preapproval_123",
        "init_point": "https://mercadopago.com/checkout/abc",
        "status": "pending",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response), \
         patch.object(payment_gateway, "_store_pending"):
        result = payment_gateway.create_checkout_link("+5491112345678")

    assert result["init_point"] == "https://mercadopago.com/checkout/abc"
    assert result["preapproval_id"] == "preapproval_123"


def test_cancel_subscription(payment_gateway):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "preapproval_123",
        "status": "cancelled",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.put", return_value=mock_response):
        result = payment_gateway.cancel_subscription("preapproval_123")

    assert result["preapproval_id"] == "preapproval_123"
    assert result["status"] == "cancelled"


def test_create_checkout_link_with_explicit_payer_email(payment_gateway):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "preapproval_999",
        "init_point": "https://mercadopago.com/checkout/xyz",
        "status": "pending",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response) as mock_post, \
         patch.object(payment_gateway, "_store_pending"):
        result = payment_gateway.create_checkout_link(
            "+5491112345678",
            payer_email="user1@example.com",
        )

    sent_body = mock_post.call_args.kwargs["json"]
    assert sent_body["payer_email"] == "user1@example.com"
    assert result["preapproval_id"] == "preapproval_999"

