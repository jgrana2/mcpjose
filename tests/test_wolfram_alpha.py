"""Tests for the Wolfram Alpha tool."""

from unittest.mock import Mock, patch
import sys
from pathlib import Path

import pytest
import requests
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.http_client import HTTPClient
from tools.wolfram_alpha import WolframAlphaClient, init_tools


class TestWolframAlphaClient:
    """Unit tests for the Wolfram Alpha client."""

    def test_init_missing_app_id(self):
        """Initialization fails without an app id."""
        with pytest.raises(EnvironmentError, match="WOLFRAM_ALPHA_APP_ID"):
            WolframAlphaClient(app_id="")

    @patch.object(HTTPClient, "get")
    def test_query_success(self, mock_get):
        """Successful query returns answer text."""
        mock_response = Mock()
        mock_response.text = "42"
        mock_get.return_value = mock_response

        http_client = HTTPClient()
        client = WolframAlphaClient(app_id="test_app_id", http_client=http_client)
        result = client.query("What is 6 * 7?", maxchars=20, units="metric")

        assert client.http.session.headers["Authorization"] == "Bearer test_app_id"
        assert result == {
            "ok": True,
            "provider": "wolfram_alpha",
            "query": "What is 6 * 7?",
            "text": "42",
        }
        assert mock_get.called
        call_args = mock_get.call_args
        assert call_args[0][0] == WolframAlphaClient.LLM_API_URL
        assert call_args[1]["params"] == {
            "input": "What is 6 * 7?",
            "maxchars": 20,
            "units": "metric",
        }

    @patch.object(HTTPClient, "get")
    def test_query_http_error(self, mock_get):
        """HTTP failures are returned as structured errors."""
        mock_response = Mock()
        mock_response.status_code = 501
        mock_response.text = "Wolfram|Alpha did not understand your input"
        mock_get.side_effect = requests.HTTPError("bad request", response=mock_response)

        client = WolframAlphaClient(app_id="test_app_id", http_client=HTTPClient())
        result = client.query("asdfghjkl")

        assert result == {
            "ok": False,
            "provider": "wolfram_alpha",
            "query": "asdfghjkl",
            "status_code": 501,
            "error": "Wolfram|Alpha did not understand your input",
        }

    def test_query_rejects_invalid_units(self):
        """Units must match the documented values."""
        client = WolframAlphaClient(app_id="test_app_id", http_client=HTTPClient())

        with pytest.raises(ValueError, match="units must be either"):
            client.query("distance to moon", units="imperial")


class TestWolframAlphaToolIntegration:
    """Integration tests for the MCP tool registration."""

    @pytest.fixture
    def mcp_server(self):
        """Create a test MCP server."""
        return FastMCP("test_wolfram_alpha")

    @pytest.mark.asyncio
    async def test_init_tools_registers_tool(self, mcp_server):
        """The Wolfram Alpha tool is registered on the server."""
        init_tools(mcp_server)
        tools = await mcp_server.list_tools()
        assert "wolfram_alpha" in [tool.name for tool in tools]

    @patch("tools.wolfram_alpha.WolframAlphaClient.query")
    @pytest.mark.asyncio
    async def test_wolfram_alpha_tool_success(self, mock_query, mcp_server, monkeypatch):
        """Registered tool delegates to the client and returns the result."""
        monkeypatch.setenv("WOLFRAM_ALPHA_APP_ID", "test_app_id")
        mock_query.return_value = {
            "ok": True,
            "provider": "wolfram_alpha",
            "query": "integrate x^2",
            "text": "x^3/3",
        }

        init_tools(mcp_server)
        tool_obj = mcp_server._tool_manager._tools["wolfram_alpha"]
        result = tool_obj.fn(query="integrate x^2")

        assert result["ok"] is True
        assert result["text"] == "x^3/3"
        mock_query.assert_called_once_with(
            query="integrate x^2",
            maxchars=None,
            units=None,
            assumption=None,
        )
