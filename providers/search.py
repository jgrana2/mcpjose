"""Search providers with unified interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from core.config import get_config
from core.utils import format_search_result


class SearchProvider(ABC):
    """Abstract base for search providers."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute search query."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search implementation using ddgs library."""

    def __init__(self):
        self._ddgs = None

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def ddgs(self):
        """Lazy initialization of DDGS client."""
        if self._ddgs is None:
            from ddgs import DDGS

            self._ddgs = DDGS()
        return self._ddgs

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        try:
            results = list(self.ddgs.text(query, max_results=max_results))

            if not results:
                return {"results": [], "message": f"No results found for: {query}"}

            formatted = [
                format_search_result(
                    title=item.get("title"),
                    snippet=item.get("body"),
                    url=item.get("href"),
                )
                for item in results
            ]
            return {"results": formatted}

        except Exception as e:
            return {"error": f"Error performing DuckDuckGo search: {str(e)}"}


class GooglePSEProvider(SearchProvider):
    """Google Programmable Search Engine implementation."""

    def __init__(self):
        self._service = None
        self.config = get_config()

    @property
    def name(self) -> str:
        return "google_pse"

    def _get_service(self):
        """Lazy initialization of Google Custom Search service."""
        if self._service is None:
            from googleapiclient.discovery import build

            api_key = self.config.google_api_key
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not configured")
            self._service = build("customsearch", "v1", developerKey=api_key)
        return self._service

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        try:
            search_engine_id = self.config.google_cse_id
            if not search_engine_id:
                return {
                    "error": "GOOGLE_CSE_ID environment variable is required for PSE search."
                }

            result = (
                self._get_service()
                .cse()
                .list(q=query, cx=search_engine_id, num=max_results)
                .execute()
            )

            items = result.get("items", [])
            if not items:
                return {"results": [], "message": f"No results found for: {query}"}

            formatted = [
                format_search_result(
                    title=item.get("title"),
                    snippet=item.get("snippet"),
                    url=item.get("link"),
                )
                for item in items
            ]
            return {"results": formatted}

        except Exception as e:
            return {"error": f"Error performing PSE search: {str(e)}"}


class SearchFactory:
    """Factory for creating search providers."""

    _providers = {
        "ddgs": DuckDuckGoProvider,
        "pse": GooglePSEProvider,
        "duckduckgo": DuckDuckGoProvider,
        "google": GooglePSEProvider,
    }

    @classmethod
    def create(cls, backend: str = None) -> SearchProvider:
        """Create search provider based on backend name.

        Args:
            backend: Backend name ('ddgs', 'pse', 'duckduckgo', 'google').
                    If None, uses configuration default.
        """
        if backend is None:
            backend = get_config().search_backend

        backend = backend.lower()
        if backend not in cls._providers:
            backend = "ddgs"  # Fallback to default

        return cls._providers[backend]()
