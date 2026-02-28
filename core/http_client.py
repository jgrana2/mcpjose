"""HTTP client wrapper with retry logic and error handling."""

from typing import Any, Dict, Optional
import requests


class HTTPClient:
    """Simple HTTP client wrapper with common configurations.

    Centralizes HTTP request logic to ensure consistent:
    - Timeout handling
    - User-Agent headers
    - Error handling patterns
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        if headers:
            self.session.headers.update(headers)

    def get(self, url: str, **kwargs) -> requests.Response:
        """Execute GET request with default timeout."""
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response

    def post(self, url: str, **kwargs) -> requests.Response:
        """Execute POST request with default timeout."""
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.post(url, **kwargs)
        response.raise_for_status()
        return response
