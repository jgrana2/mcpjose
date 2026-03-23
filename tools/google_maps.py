"""Google Maps Places API tools for MCP server."""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP


def init_tools(mcp: FastMCP) -> None:
    """Initialize Google Maps tools for MCP server.

    Args:
        mcp: FastMCP server instance
    """
    # Delegate tool behavior to the canonical shared registry implementation.
    from langchain_agent.tool_registry import ProjectToolRegistry

    registry = ProjectToolRegistry()

    @mcp.tool()
    def search_places(
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        place_type: Optional[str] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Search for places using Google Maps Places API.

        Args:
            query: Search query (e.g., "coffee shop", "restaurants")
            location: Optional location bias as "lat,lng" or address
            radius: Optional search radius in meters
            place_type: Optional place type filter
            max_results: Maximum number of results to return (default: 5)

        Returns:
            Dictionary with search results or error
        """
        return registry.search_places(
            query=query,
            location=location,
            radius=radius,
            place_type=place_type,
            max_results=max_results,
        )

    @mcp.tool()
    def get_place_details(place_id: str) -> Dict[str, Any]:
        """Get detailed information about a place.

        Args:
            place_id: Google Maps Place ID

        Returns:
            Dictionary with place details or error
        """
        return registry.get_place_details(place_id)
