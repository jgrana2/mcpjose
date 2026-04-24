"""Navigation tool for web browsing and PDF content extraction."""

import io
import logging
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

from core.http_client import HTTPClient
from core.utils import clean_text_whitespace, is_pdf_file

logger = logging.getLogger(__name__)


def extract_pdf_content(url: str, http_client: HTTPClient) -> Optional[str]:
    """Download and extract text from a PDF URL.

    Args:
        url: URL pointing to a PDF file.
        http_client: HTTP client for downloading.

    Returns:
        Extracted text formatted as markdown, or None if not a PDF.
    """
    try:
        response = http_client.get(url)

        # Verify Content-Type for non-PDF extensions
        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type.lower() and not is_pdf_file(url):
            return None

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        pages: list[str] = []
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            if text.strip():
                pages.append(f"## Page {page_num}\n\n{text.strip()}")

        return "\n\n---\n\n".join(pages)

    except Exception as e:
        logger.debug("PDF extraction error: %s", e)
        return None


def extract_html_content(url: str, http_client: HTTPClient) -> Dict[str, Any]:
    """Fetch and extract text, links, and image sources from an HTML page.

    Args:
        url: URL to fetch.
        http_client: HTTP client for downloading.

    Returns:
        Dictionary with 'text', 'links', and 'images'.
    """
    response = http_client.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script, style, nav, header, footer
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    text = clean_text_whitespace(soup.get_text())
    links = [
        {"text": a.get_text(strip=True), "href": a.get("href")}
        for a in soup.find_all("a", href=True)
    ]
    images = [img.get("src") for img in soup.find_all("img", src=True)]

    return {
        "text": text,
        "links": links,
        "images": images,
    }


def init_tools(mcp: FastMCP, http_client: Optional[HTTPClient] = None) -> None:
    """Initialize navigation tools with the MCP server.

    Args:
        mcp: FastMCP server instance.
        http_client: Optional custom HTTP client (for testing/dependency injection).
    """
    # Delegate tool behavior to the canonical shared registry implementation.
    from langchain_agent.tool_registry import ProjectToolRegistry

    registry = ProjectToolRegistry()

    @mcp.tool()
    def navigate_to_url(url: str) -> Dict[str, Any]:
        """Navigate to a URL and extract content. Supports HTML and PDF.

        Args:
            url: The URL to navigate to.

        Returns:
            Dictionary with 'content' (for PDF) or 'text', 'links', 'images' (for HTML), 'url', and 'type' keys.
        """
        return registry.navigate_to_url(url)
