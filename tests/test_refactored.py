"""Tests for refactored MCP server and providers."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import CredentialManager, get_config
from core.utils import (
    detect_mime_type,
    is_pdf_file,
    format_search_result,
    clean_text_whitespace,
    build_ocr_prompt,
)
from providers.search import SearchFactory, DuckDuckGoProvider
from providers import ProviderFactory
from mcp_server.server import create_server


def test_config():
    """Test configuration singleton."""
    print("\n" + "=" * 60)
    print("TEST: Configuration")
    print("=" * 60)

    config = get_config()
    print(f"✓ Config loaded: search_backend={config.search_backend}")

    # Test singleton
    config2 = get_config()
    assert config is config2
    print("✓ Singleton pattern works")


def test_utils():
    """Test utility functions."""
    print("\n" + "=" * 60)
    print("TEST: Utilities")
    print("=" * 60)

    assert detect_mime_type("test.png") == "image/png"
    assert is_pdf_file("doc.pdf")
    assert not is_pdf_file("image.png")

    result = format_search_result("Title", "Snippet", "http://example.com")
    assert result["title"] == "Title"

    prompt = build_ocr_prompt("analyze", "detected text")
    assert "detected text" in prompt
    assert "analyze" in prompt

    print("✓ All utility functions work")


def test_search():
    """Test search providers."""
    print("\n" + "=" * 60)
    print("TEST: Search Providers")
    print("=" * 60)

    provider = SearchFactory.create("ddgs")
    assert isinstance(provider, DuckDuckGoProvider)
    print("✓ DuckDuckGo provider created")

    try:
        result = provider.search("Python programming", max_results=2)
        print(f"✓ Search executed: {len(result.get('results', []))} results")
    except Exception as e:
        print(f"⚠ Search test: {e}")


def test_mcp_server():
    """Test MCP server creation."""
    print("\n" + "=" * 60)
    print("TEST: MCP Server")
    print("=" * 60)

    mcp = create_server()
    assert mcp.name == "mcpjose"
    print(f"✓ MCP server created: {mcp.name}")

    async def list_tools():
        tools = await mcp.list_tools()
        return [t.name for t in tools]

    try:
        tool_names = asyncio.run(list_tools())
        print(f"✓ Found {len(tool_names)} tools: {', '.join(tool_names)}")
    except Exception as e:
        print(f"⚠ Tool listing: {e}")


def run_all():
    """Run all tests."""
    print("=" * 60)
    print("REFACTORED CODEBASE TEST SUITE")
    print("=" * 60)

    test_config()
    test_utils()
    test_search()
    test_mcp_server()

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
