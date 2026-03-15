"""Google Maps Places API tools for MCP server."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from providers import ProviderFactory

logger = logging.getLogger(__name__)


def init_tools(mcp: FastMCP) -> None:
    """Initialize Google Maps tools for MCP server.

    Args:
        mcp: FastMCP server instance
    """
    # Create provider instance with graceful error handling
    maps_provider = None
    try:
        maps_provider = ProviderFactory.create_maps("google")
    except Exception as e:
        logger.warning("Could not initialize Google Maps: %s", e)
        return

    if maps_provider:

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
            try:
                results = maps_provider.search_places(
                    query=query,
                    location=location,
                    radius=radius,
                    place_type=place_type,
                    max_results=max_results,
                )

                return {
                    "success": True,
                    "query": query,
                    "count": len(results),
                    "results": results,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "query": query,
                }

        @mcp.tool()
        def get_place_details(place_id: str) -> Dict[str, Any]:
            """Get detailed information about a place.

            Args:
                place_id: Google Maps Place ID

            Returns:
                Dictionary with place details or error
            """
            try:
                details = maps_provider.get_place_details(place_id)

                return {
                    "success": True,
                    "place_id": place_id,
                    "details": details,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "place_id": place_id,
                }
