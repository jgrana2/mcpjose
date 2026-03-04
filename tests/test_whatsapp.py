"""Tests for WhatsApp messaging tool.

This module tests the WhatsApp Cloud API integration including:
- Rate limiting
- Destination validation
- Message sending
- Error handling
"""

import pytest
from unittest.mock import Mock, patch
from mcp.server.fastmcp import FastMCP

from tools.whatsapp import (
    WhatsAppCloudAPIClient,
    WhatsAppSendResult,
    _normalize_e164ish,
    _parse_csv_set,
    init_tools,
)
from core.http_client import HTTPClient


class TestNormalization:
    """Test phone number normalization."""

    def test_normalize_e164ish_with_plus(self):
        """Test normalization removes leading plus."""
        assert _normalize_e164ish("+14155551234") == "14155551234"

    def test_normalize_e164ish_without_plus(self):
        """Test normalization of number without plus."""
        assert _normalize_e164ish("14155551234") == "14155551234"

    def test_normalize_e164ish_with_spaces(self):
        """Test normalization removes spaces."""
        assert _normalize_e164ish("+1 415 555 1234") == "14155551234"

    def test_normalize_e164ish_with_dashes(self):
        """Test normalization removes dashes."""
        assert _normalize_e164ish("+1-415-555-1234") == "14155551234"

    def test_normalize_e164ish_with_parens(self):
        """Test normalization removes parentheses."""
        assert _normalize_e164ish("+1 (415) 555-1234") == "14155551234"


class TestCSVParsing:
    """Test CSV set parsing."""

    def test_parse_csv_set_single(self):
        """Test parsing single value."""
        assert _parse_csv_set("14155551234") == {"14155551234"}

    def test_parse_csv_set_multiple(self):
        """Test parsing multiple values."""
        assert _parse_csv_set("14155551234,14155551235") == {
            "14155551234",
            "14155551235",
        }

    def test_parse_csv_set_with_spaces(self):
        """Test parsing with spaces."""
        assert _parse_csv_set(" 14155551234 , 14155551235 ") == {
            "14155551234",
            "14155551235",
        }

    def test_parse_csv_set_empty(self):
        """Test parsing empty string."""
        assert _parse_csv_set("") == set()
        assert _parse_csv_set(None) == set()


class TestWhatsAppSendResult:
    """Test WhatsAppSendResult dataclass."""

    def test_to_dict_success(self):
        """Test conversion to dict for successful send."""
        result = WhatsAppSendResult(
            ok=True,
            destination="14155551234",
            provider="whatsapp_cloud_api",
            message_id="wamid.xxx",
            rate_limit_day="2026-03-03",
            rate_limit_used=1,
            rate_limit_limit=10,
            rate_limit_remaining=9,
        )
        data = result.to_dict()
        assert data["ok"] is True
        assert data["destination"] == "14155551234"
        assert data["provider"] == "whatsapp_cloud_api"
        assert data["message_id"] == "wamid.xxx"
        assert data["rate_limit"]["day"] == "2026-03-03"
        assert data["rate_limit"]["used"] == 1
        assert data["rate_limit"]["limit"] == 10
        assert data["rate_limit"]["remaining"] == 9

    def test_to_dict_error(self):
        """Test conversion to dict for failed send."""
        result = WhatsAppSendResult(
            ok=False,
            destination="14155551234",
            provider="whatsapp_cloud_api",
            error="Rate limit exceeded",
        )
        data = result.to_dict()
        assert data["ok"] is False
        assert data["error"] == "Rate limit exceeded"
        assert "message_id" not in data
        assert "rate_limit" not in data


class TestWhatsAppCloudAPIClient:
    """Test WhatsApp Cloud API client."""

    def test_init_missing_token(self):
        """Test initialization fails without access token."""
        with pytest.raises(EnvironmentError, match="WHATSAPP_ACCESS_TOKEN"):
            WhatsAppCloudAPIClient(access_token="", phone_number_id="123456")

    def test_init_missing_phone_id(self):
        """Test initialization fails without phone number ID."""
        with pytest.raises(EnvironmentError, match="WHATSAPP_PHONE_NUMBER_ID"):
            WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="")

    def test_init_success(self):
        """Test successful initialization."""
        client = WhatsAppCloudAPIClient(
            access_token="test_token", phone_number_id="123456"
        )
        assert client.access_token == "test_token"
        assert client.phone_number_id == "123456"
        assert client.api_version == "v21.0"
        assert client.name == "whatsapp_cloud_api"

    @patch.object(HTTPClient, "post")
    def test_send_text_message(self, mock_post):
        """Test sending a text message."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}],
            "messaging_product": "whatsapp",
        }
        mock_post.return_value = mock_response

        client = WhatsAppCloudAPIClient(
            access_token="test_token", phone_number_id="123456"
        )
        _ = client.send_text_message("+14155551234", "Test message")

        assert mock_post.called
        call_args = mock_post.call_args
        assert "v21.0/123456/messages" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "14155551234"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Test message"

    @patch.object(HTTPClient, "post")
    def test_send_template_message(self, mock_post):
        """Test sending a template message."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}],
            "messaging_product": "whatsapp",
        }
        mock_post.return_value = mock_response

        client = WhatsAppCloudAPIClient(
            access_token="test_token", phone_number_id="123456"
        )
        _ = client.send_text_message(
            "+14155551234", "Test message", template_name="hello_world"
        )

        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "hello_world"
        assert payload["template"]["language"]["code"] == "en_US"


class TestWhatsAppToolIntegration:
    """Integration tests for WhatsApp tool."""

    @pytest.fixture
    def mcp_server(self):
        """Create a test MCP server."""
        return FastMCP("test_whatsapp")

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
        monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
        monkeypatch.setenv("WHATSAPP_DEFAULT_DESTINATION", "+14155551234")
        monkeypatch.setenv("WHATSAPP_DAILY_MAX", "10")

    @pytest.mark.asyncio
    async def test_init_tools(self, mcp_server, mock_env):
        """Test tool initialization."""
        init_tools(mcp_server)
        # Check that the tool was registered
        tools = await mcp_server.list_tools()
        assert "send_ws_msg" in [tool.name for tool in tools]

    @patch("tools.whatsapp.WhatsAppCloudAPIClient.send_text_message")
    @patch("tools.whatsapp.DailyRateLimiter.from_env")
    @pytest.mark.asyncio
    async def test_send_ws_msg_success(
        self, mock_limiter_factory, mock_send, mcp_server, mock_env
    ):
        """Test successful message sending."""
        # Mock rate limiter
        mock_limiter = Mock()
        mock_rate_result = Mock()
        mock_rate_result.allowed = True
        mock_rate_result.day = "2026-03-03"
        mock_rate_result.used = 1
        mock_rate_result.limit = 10
        mock_rate_result.remaining = 9
        mock_limiter.consume.return_value = mock_rate_result
        mock_limiter_factory.return_value = mock_limiter

        # Mock API response
        mock_send.return_value = {"messages": [{"id": "wamid.test123"}]}

        init_tools(mcp_server)
        tools = await mcp_server.list_tools()
        _ = next(t for t in tools if t.name == "send_ws_msg")
        
        # Get the tool function directly from the internal manager
        tool_obj = mcp_server._tool_manager._tools["send_ws_msg"]
        result = tool_obj.fn(destination=None, message="Test message")

        assert result["ok"] is True
        assert result["destination"] == "14155551234"
        assert result["message_id"] == "wamid.test123"
        assert result["rate_limit"]["remaining"] == 9

    @patch("tools.whatsapp.DailyRateLimiter.from_env")
    @pytest.mark.asyncio
    async def test_send_ws_msg_rate_limit(
        self, mock_limiter_factory, mcp_server, mock_env
    ):
        """Test rate limit enforcement."""
        # Mock rate limiter - limit exceeded
        mock_limiter = Mock()
        mock_rate_result = Mock()
        mock_rate_result.allowed = False
        mock_rate_result.day = "2026-03-03"
        mock_rate_result.used = 10
        mock_rate_result.limit = 10
        mock_rate_result.remaining = 0
        mock_limiter.consume.return_value = mock_rate_result
        mock_limiter_factory.return_value = mock_limiter

        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["send_ws_msg"]
        result = tool_obj.fn(destination=None, message="Test message")

        assert result["ok"] is False
        assert "rate limit exceeded" in result["error"].lower()
        assert result["rate_limit"]["remaining"] == 0

    @patch("tools.whatsapp.DailyRateLimiter.from_env")
    @pytest.mark.asyncio
    async def test_send_ws_msg_missing_destination(self, mock_limiter_factory, mcp_server, monkeypatch):
        """Test error when destination is not configured."""
        # Mock rate limiter first
        mock_limiter = Mock()
        mock_rate_result = Mock()
        mock_rate_result.allowed = True
        mock_rate_result.day = "2026-03-03"
        mock_rate_result.used = 0
        mock_rate_result.limit = 10
        mock_rate_result.remaining = 10
        mock_limiter.consume.return_value = mock_rate_result
        mock_limiter_factory.return_value = mock_limiter
        
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
        # Explicitly unset the destination
        monkeypatch.delenv("WHATSAPP_DEFAULT_DESTINATION", raising=False)

        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["send_ws_msg"]
        result = tool_obj.fn(destination=None, message="Test message")

        assert result["ok"] is False
        assert "Missing predefined destination" in result["error"]

    @pytest.mark.asyncio
    async def test_send_ws_msg_empty_message(self, mcp_server, mock_env):
        """Test error when message is empty."""
        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["send_ws_msg"]
        result = tool_obj.fn(destination=None, message="")

        assert result["ok"] is False
        assert "non-empty string" in result["error"]

    @pytest.mark.asyncio
    async def test_send_ws_msg_destination_mismatch(self, mcp_server, mock_env):
        """Test error when destination doesn't match default."""
        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["send_ws_msg"]
        result = tool_obj.fn(destination="+19998887777", message="Test")

        assert result["ok"] is False
        assert "Destination is fixed" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
