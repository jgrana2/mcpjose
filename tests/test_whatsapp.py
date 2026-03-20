"""Tests for WhatsApp messaging tool.

This module tests the WhatsApp Cloud API integration including:
- Rate limiting
- Destination validation
- Message sending
- Error handling
- Media sending
"""

from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from core.http_client import HTTPClient
from tools.whatsapp import (
    WhatsAppCloudAPIClient,
    WhatsAppSendResult,
    _normalize_e164ish,
    _parse_csv_set,
    init_tools,
)


class TestNormalization:
    """Test phone number normalization."""

    def test_normalize_e164ish_with_plus(self):
        assert _normalize_e164ish("+14155551234") == "14155551234"

    def test_normalize_e164ish_without_plus(self):
        assert _normalize_e164ish("14155551234") == "14155551234"

    def test_normalize_e164ish_with_spaces(self):
        assert _normalize_e164ish("+1 415 555 1234") == "14155551234"

    def test_normalize_e164ish_with_dashes(self):
        assert _normalize_e164ish("+1-415-555-1234") == "14155551234"

    def test_normalize_e164ish_with_parens(self):
        assert _normalize_e164ish("+1 (415) 555-1234") == "14155551234"


class TestCSVParsing:
    def test_parse_csv_set_single(self):
        assert _parse_csv_set("14155551234") == {"14155551234"}

    def test_parse_csv_set_multiple(self):
        assert _parse_csv_set("14155551234,14155551235") == {"14155551234", "14155551235"}

    def test_parse_csv_set_with_spaces(self):
        assert _parse_csv_set(" 14155551234 , 14155551235 ") == {"14155551234", "14155551235"}

    def test_parse_csv_set_empty(self):
        assert _parse_csv_set("") == set()
        assert _parse_csv_set(None) == set()


class TestWhatsAppSendResult:
    def test_to_dict_success(self):
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
        assert data["message_id"] == "wamid.xxx"

    def test_to_dict_error(self):
        result = WhatsAppSendResult(
            ok=False,
            destination="14155551234",
            provider="whatsapp_cloud_api",
            error="Rate limit exceeded",
        )
        data = result.to_dict()
        assert data["ok"] is False
        assert data["error"] == "Rate limit exceeded"


class TestWhatsAppCloudAPIClient:
    def test_init_missing_token(self):
        with pytest.raises(EnvironmentError, match="WHATSAPP_ACCESS_TOKEN"):
            WhatsAppCloudAPIClient(access_token="", phone_number_id="123456")

    def test_init_missing_phone_id(self):
        with pytest.raises(EnvironmentError, match="WHATSAPP_PHONE_NUMBER_ID"):
            WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="")

    def test_init_success(self):
        client = WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="123456")
        assert client.name == "whatsapp_cloud_api"

    @patch.object(HTTPClient, "post")
    def test_send_text_message(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        mock_post.return_value = mock_response
        client = WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="123456")
        _ = client.send_text_message("+14155551234", "Test message")
        payload = mock_post.call_args[1]["json"]
        assert payload["type"] == "text"

    @patch.object(HTTPClient, "post")
    def test_send_template_message(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        mock_post.return_value = mock_response
        client = WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="123456")
        _ = client.send_text_message(
            "+14155551234", "Test message", template_name="hello_world"
        )
        payload = mock_post.call_args[1]["json"]
        assert payload["type"] == "template"

    @patch.object(HTTPClient, "post")
    def test_upload_media(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"id": "media_123"}
        mock_post.return_value = mock_response
        with NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"pngdata")
            tmp.flush()
            client = WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="123456")
            media_id = client.upload_media(tmp.name, mime_type="image/png")
        assert media_id == "media_123"

    @patch.object(HTTPClient, "post")
    def test_send_image_message(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.image123"}]}
        mock_post.return_value = mock_response
        client = WhatsAppCloudAPIClient(access_token="test_token", phone_number_id="123456")
        _ = client.send_image_message("+14155551234", media_id="media_123", caption="Hello")
        payload = mock_post.call_args[1]["json"]
        assert payload["type"] == "image"
        assert payload["image"]["caption"] == "Hello"


class TestWhatsAppToolIntegration:
    @pytest.fixture
    def mcp_server(self):
        return FastMCP("test_whatsapp")

    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
        monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
        monkeypatch.setenv("WHATSAPP_DEFAULT_DESTINATION", "+14155551234")
        monkeypatch.setenv("WHATSAPP_DAILY_MAX", "10")

    @pytest.mark.asyncio
    async def test_init_tools(self, mcp_server, mock_env):
        init_tools(mcp_server)
        tools = await mcp_server.list_tools()
        assert "send_ws_msg" in [tool.name for tool in tools]

    @patch("tools.whatsapp.DailyRateLimiter.from_env")
    @patch("tools.whatsapp.WhatsAppCloudAPIClient.send_text_message")
    @pytest.mark.asyncio
    async def test_send_ws_msg_success(self, mock_send, mock_limiter_factory, mcp_server, mock_env):
        mock_limiter = Mock()
        mock_rate_result = Mock(allowed=True, day="2026-03-03", used=1, limit=10, remaining=9)
        mock_limiter.consume.return_value = mock_rate_result
        mock_limiter_factory.return_value = mock_limiter
        mock_send.return_value = {"messages": [{"id": "wamid.test123"}]}
        init_tools(mcp_server)
        result = mcp_server._tool_manager._tools["send_ws_msg"].fn(destination=None, message="Test message")
        assert result["ok"] is True
        assert result["message_id"] == "wamid.test123"

    @patch("tools.whatsapp.DailyRateLimiter.from_env")
    @pytest.mark.asyncio
    async def test_send_ws_msg_image_path_uses_media_flow(self, mock_limiter_factory, mcp_server, mock_env):
        mock_limiter = Mock()
        mock_rate_result = Mock(allowed=True, day="2026-03-03", used=1, limit=10, remaining=9)
        mock_limiter.consume.return_value = mock_rate_result
        mock_limiter_factory.return_value = mock_limiter
        with patch("tools.whatsapp.WhatsAppCloudAPIClient.upload_media", return_value="media_123") as mock_upload:
            with patch("tools.whatsapp.WhatsAppCloudAPIClient.send_image_message", return_value={"messages": [{"id": "wamid.img"}]}) as mock_send_image:
                init_tools(mcp_server)
                result = mcp_server._tool_manager._tools["send_ws_msg"].fn(
                    destination=None,
                    message="Caption text",
                    image_path="/tmp/generated.png",
                )
                assert result["ok"] is True
                assert result["message_id"] == "wamid.img"
                mock_upload.assert_called_once()
                mock_send_image.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
