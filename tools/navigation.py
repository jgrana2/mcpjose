"""Navigation tool for web browsing and PDF content extraction."""

import io
import logging
from html.parser import HTMLParser
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

from core.http_client import HTTPClient
from core.utils import clean_text_whitespace, is_pdf_file

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extract text content from HTML, filtering out script/style tags."""

    SKIP_TAGS = {"script", "style", "nav", "header", "footer"}
    BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.current_tag: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.current_tag = tag
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")
        self.current_tag = None

    def handle_data(self, data: str) -> None:
        if self.current_tag not in self.SKIP_TAGS:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


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


def extract_html_content(url: str, http_client: HTTPClient) -> str:
    """Fetch and extract text content from an HTML page.

    Args:
        url: URL to fetch.
        http_client: HTTP client for downloading.

    Returns:
        Extracted text content.
    """
    response = http_client.get(url)

    extractor = HTMLTextExtractor()
    extractor.feed(response.text)

    return clean_text_whitespace(extractor.get_text())


def init_tools(mcp: FastMCP, http_client: Optional[HTTPClient] = None) -> None:
    """Initialize navigation tools with the MCP server.

    Args:
        mcp: FastMCP server instance.
        http_client: Optional custom HTTP client (for testing/dependency injection).
    """
    client = http_client or HTTPClient()

    @mcp.tool()
    def navigate_to_url(url: str) -> Dict[str, Any]:
        """Navigate to a URL and extract content. Supports HTML and PDF.

        Args:
            url: The URL to navigate to.

        Returns:
            Dictionary with 'content', 'url', and 'type' keys.
        """
        try:
            # Try PDF extraction first for PDF URLs
            if is_pdf_file(url):
                pdf_content = extract_pdf_content(url, client)
                if pdf_content:
                    return {"content": pdf_content, "url": url, "type": "pdf"}

            # Fall back to HTML extraction
            content = extract_html_content(url, client)
            return {"content": content, "url": url, "type": "html"}

        except Exception as e:
            return {"error": f"Error navigating to {url}: {str(e)}", "url": url}
