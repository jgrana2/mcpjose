"""Wolfram Alpha tool integration."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from mcp.server.fastmcp import FastMCP

from core.config import get_config
from core.http_client import HTTPClient


class WolframAlphaClient:
    """Minimal client for the Wolfram Alpha LLM API."""

    LLM_API_URL = "https://www.wolframalpha.com/api/v1/llm-api"
    VALID_UNITS = {"metric", "nonmetric"}

    def __init__(
        self,
        app_id: str,
        http_client: Optional[HTTPClient] = None,
    ):
        if not app_id:
            raise EnvironmentError("WOLFRAM_ALPHA_APP_ID is not set")

        self.app_id = app_id
        self.http = http_client or HTTPClient()
        self.http.session.headers.update({"Authorization": f"Bearer {app_id}"})

    @property
    def name(self) -> str:
        return "wolfram_alpha"

    def query(
        self,
        query: str,
        maxchars: Optional[int] = None,
        units: Optional[str] = None,
        assumption: Optional[str] = None,
    ) -> Dict[str, Any]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Query must be a non-empty string.")

        if maxchars is not None and maxchars <= 0:
            raise ValueError("maxchars must be greater than 0.")

        normalized_units = units.strip().lower() if units else None
        if normalized_units and normalized_units not in self.VALID_UNITS:
            raise ValueError("units must be either 'metric' or 'nonmetric'.")

        params: Dict[str, Any] = {"input": cleaned_query}
        if maxchars is not None:
            params["maxchars"] = maxchars
        if normalized_units:
            params["units"] = normalized_units
        if assumption:
            params["assumption"] = assumption.strip()

        try:
            response = self.http.get(self.LLM_API_URL, params=params)
        except requests.HTTPError as exc:
            error_response = exc.response
            if error_response is None:
                return {
                    "ok": False,
                    "provider": self.name,
                    "query": cleaned_query,
                    "error": str(exc),
                }

            return {
                "ok": False,
                "provider": self.name,
                "query": cleaned_query,
                "status_code": error_response.status_code,
                "error": error_response.text.strip() or str(exc),
            }

        return {
            "ok": True,
            "provider": self.name,
            "query": cleaned_query,
            "text": response.text.strip(),
        }


def init_tools(mcp: FastMCP, http_client: Optional[HTTPClient] = None) -> None:
    """Register Wolfram Alpha tools."""
    # Delegate tool behavior to the canonical shared registry implementation.
    from langchain_agent.tool_registry import ProjectToolRegistry

    registry = ProjectToolRegistry()

    @mcp.tool()
    def wolfram_alpha(
        query: str,
        maxchars: Optional[int] = None,
        units: Optional[str] = None,
        assumption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query Wolfram Alpha's LLM API for computed or factual answers.

        Inputs:
            query: Natural-language or mathematical query to evaluate.
            maxchars: Optional response length cap in characters.
            units: Optional units system ('metric' or 'nonmetric').
            assumption: Optional Wolfram Alpha assumption string to disambiguate the query.

        Outputs:
            ok: Whether the request succeeded.
            text: Wolfram Alpha's plain-text answer when successful.
            error: Error message and HTTP status code when unsuccessful.
        """
        return registry.wolfram_alpha(
            query=query,
            maxchars=maxchars,
            units=units,
            assumption=assumption,
        )
