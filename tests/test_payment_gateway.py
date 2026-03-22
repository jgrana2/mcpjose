import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tools.payment_gateway import PaymentGatewayTool
from core.http_client import HTTPClient

@pytest.fixture
def http_client():
    client = MagicMock(spec=HTTPClient)
    return client

@pytest.fixture
def payment_gateway(http_client):
    with patch('core.config.CredentialManager') as MockCreds:
        # Mocking credentials
        creds_instance = MockCreds.return_value
        creds_instance.get_api_key.return_value = "APP_USR-test-token"
        
        pg = PaymentGatewayTool(http_client)
        pg.creds = creds_instance
        return pg

@pytest.mark.asyncio
async def test_get_subscription_success(payment_gateway):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "authorized", "id": "preapproval_123"}
    
    payment_gateway.http_client.get.return_value = mock_response

    result = await payment_gateway.get_subscription("preapproval_123")
    
    assert result == {"status": "authorized", "id": "preapproval_123"}
    payment_gateway.http_client.get.assert_called_once_with(
        "https://api.mercadopago.com/preapproval/preapproval_123",
        headers={'Authorization': 'Bearer APP_USR-test-token', 'Content-Type': 'application/json'}
    )

@pytest.mark.asyncio
async def test_execute_tool(payment_gateway):
    with patch.object(payment_gateway, 'get_subscription', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"status": "authorized", "reason": "Monthly Plan"}
        
        result = await payment_gateway.execute("mp_check_subscription", {"subscription_id": "sub_456"})
        
        assert len(result) == 1
        assert "authorized" in result[0].text
        assert "Monthly Plan" in result[0].text
