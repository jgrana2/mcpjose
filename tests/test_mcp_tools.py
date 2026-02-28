#!/usr/bin/env python3
"""Test MCP server tools."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.server import create_server


def test_mcp():
    """Test MCP server."""
    print("=" * 60)
    print("MCP SERVER TESTS")
    print("=" * 60)

    mcp = create_server()
    print(f"✓ Server created: {mcp.name}")

    async def run_tests():
        tools = await mcp.list_tools()
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}")

    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"⚠ Error: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_mcp()
