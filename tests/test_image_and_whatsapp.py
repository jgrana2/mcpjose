"""Tests for combined image generation and WhatsApp sending tool."""

from unittest.mock import Mock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from tools.image_and_whatsapp import init_tools


class TestImageAndWhatsAppTool:
    @pytest.fixture
    def mcp_server(self):
        return FastMCP("test_image_and_whatsapp")

    @pytest.fixture
    def mock_env(self, monkeypatch):
        monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test_token")
        monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
        monkeypatch.setenv("WHATSAPP_API_VERSION", "v22.0")
        monkeypatch.setenv("WHATSAPP_DEFAULT_DESTINATION", "+14155551234")

    @pytest.mark.asyncio
    async def test_init_tools_registers_tool(self, mcp_server, mock_env):
        init_tools(mcp_server)
        tools = await mcp_server.list_tools()
        assert "generate_and_send_image" in [tool.name for tool in tools]

    @patch("tools.image_and_whatsapp.ProviderFactory.create_image_generator")
    @patch("tools.image_and_whatsapp.WhatsAppCloudAPIClient.send_image_message")
    @patch("tools.image_and_whatsapp.WhatsAppCloudAPIClient.upload_media")
    @pytest.mark.asyncio
    async def test_generate_and_send_image_success(
        self, mock_upload, mock_send, mock_image_factory, mcp_server, mock_env
    ):
        mock_image_gen = Mock()
        mock_image_gen.generate.return_value = {
            "image_path": "/tmp/generated.png",
            "text": "Generated image",
        }
        mock_image_factory.return_value = mock_image_gen
        mock_upload.return_value = "media_123"
        mock_send.return_value = {"messages": [{"id": "wamid.test123"}]}

        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["generate_and_send_image"]
        result = tool_obj.fn(prompt="a red car")

        assert result["ok"] is True
        assert result["generation"]["image_path"] == "/tmp/generated.png"
        assert result["media_id"] == "media_123"
        assert "send" in result
