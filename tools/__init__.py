"""MCP tools package - now refactored into providers and core modules."""

# Navigation is the only remaining tool here, search moved to providers
from tools.navigation import init_tools as init_navigation_tools

__all__ = ["init_navigation_tools"]
