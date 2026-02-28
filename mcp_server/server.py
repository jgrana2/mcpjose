"""Unified MCP server with all tools."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from twscrape import API
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add scrape_play directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scrape_play"))

from mcp.server.fastmcp import FastMCP

# Import providers
from providers import ProviderFactory
from providers.search import SearchFactory
from tools.navigation import init_tools as init_navigation_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tools.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP("mcpjose")

    # Initialize navigation tools
    init_navigation_tools(mcp)

    # Initialize search tools
    _init_search_tools(mcp)

    # Initialize AI tools
    _init_ai_tools(mcp)

    return mcp


def _init_search_tools(mcp: FastMCP) -> None:
    """Initialize search tools."""

    @mcp.tool()
    def search(query: str) -> Dict[str, Any]:
        """Search the web using the configured backend (DuckDuckGo or Google).

        Uses the `SEARCH_ENGINE` environment variable:
        - `ddgs` => DuckDuckGo
        - `pse`  => Google (PSE / Googling)

        Args:
            query: The search query.

        Returns:
            Dictionary with search results or error.
        """
        provider = SearchFactory.create()
        return provider.search(query)


def _init_ai_tools(mcp: FastMCP) -> None:
    """Initialize AI-powered tools."""

    # Create provider instances (lazy initialization inside providers)
    # Handle missing credentials gracefully
    openai_vision = None
    gemini_vision = None
    openai_llm = None
    image_gen = None
    ocr = None

    try:
        openai_vision = ProviderFactory.create_vision("openai")
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI vision: {e}")

    try:
        gemini_vision = ProviderFactory.create_vision("gemini")
    except Exception as e:
        print(f"Warning: Could not initialize Gemini vision: {e}")

    try:
        openai_llm = ProviderFactory.create_llm("openai")
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI LLM: {e}")

    try:
        image_gen = ProviderFactory.create_image_generator("gemini")
    except Exception as e:
        print(f"Warning: Could not initialize Gemini image generator: {e}")

    try:
        ocr = ProviderFactory.create_ocr("google")
    except Exception as e:
        print(f"Warning: Could not initialize Google OCR: {e}")

    if openai_llm:

        @mcp.tool()
        def call_llm(prompt: str) -> Dict[str, str]:
            """Generate text using OpenAI LLM.

            Args:
                prompt: The prompt text.

            Returns:
                Dictionary with 'text' key containing the response.
            """
            result = openai_llm.complete(prompt)
            return {"text": result}

    if openai_vision:

        @mcp.tool()
        def openai_vision_tool(
            image_path: str,
            prompt: str,
            ocr_context: Optional[str] = None,
            ocr_file: Optional[str] = None,
            model: Optional[str] = None,
        ) -> Dict[str, str]:
            """Process image with OpenAI vision model.

            Args:
                image_path: Path to image or PDF.
                prompt: Text prompt.
                ocr_context: Optional OCR context text.
                ocr_file: Optional path to file containing OCR context.
                model: Optional model override.

            Returns:
                Dictionary with 'text' key containing the response.
            """
            if ocr_file:
                from core.utils import load_text_file

                ocr_context = load_text_file(ocr_file)

            result = openai_vision.process_image(
                image_path=image_path,
                prompt=prompt,
                ocr_context=ocr_context,
                model=model,
            )
            return {"text": result}

    if gemini_vision:

        @mcp.tool()
        def gemini_vision_tool(
            image_path: str,
            prompt: str,
            ocr_context: Optional[str] = None,
            ocr_file: Optional[str] = None,
        ) -> Dict[str, str]:
            """Process image with Gemini vision model.

            Args:
                image_path: Path to image or PDF.
                prompt: Text prompt.
                ocr_context: Optional OCR context text.
                ocr_file: Optional path to file containing OCR context.

            Returns:
                Dictionary with 'text' key containing the response.
            """
            if ocr_file:
                from core.utils import load_text_file

                ocr_context = load_text_file(ocr_file)

            result = gemini_vision.process_image(
                image_path=image_path,
                prompt=prompt,
                ocr_context=ocr_context,
            )
            return {"text": result}

    if image_gen:

        @mcp.tool()
        def generate_image(
            prompt: str,
            output_path: Optional[str] = None,
            image_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Generate an image from a text prompt using Gemini.

            Args:
                prompt: Text description of the image.
                output_path: Optional path to save the image.
                image_path: Optional path to an input image for editing/modification.

            Returns:
                Dictionary with 'text' and/or 'image_path' keys.
            """
            return image_gen.generate(prompt, output_path, image_path)

    if ocr:

        @mcp.tool()
        def google_ocr(
            input_file: str,
            file_type: Optional[str] = None,
            output: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Extract text from images or PDFs using Google Vision OCR.

            Args:
                input_file: Path to the file.
                file_type: Optional type ('pdf' or 'image'). Auto-detected if not specified.
                output: Optional path to save annotations.

            Returns:
                Dictionary with 'annotations' and optionally 'output_path'.
            """
            annotations = ocr.extract_text(input_file, file_type)

            result: Dict[str, Any] = {"annotations": annotations}
            if output:
                ocr.save_annotations(annotations, output)
                result["output_path"] = output

            return result

    # Summary generator tool based on scrape_play.py mode 's'
    @mcp.tool()
    async def x_search(
        topic: str,
    ) -> Dict[str, Any]:
        """Search for tweets about a topic and return their content.

        Searches X (Twitter) for recent tweets about the given topic,
        filtering for tweets that contain links. Returns up to 20 tweets.

        Args:
            topic: The search topic/query

        Returns:
            Dictionary with 'text' (concatenated tweets), 'count' (int), and 'topic'
        """

        api = API()
        # Add account from environment variables
        username = os.getenv("TWSCRAPE_USERNAME")
        password = os.getenv("TWSCRAPE_PASSWORD")
        email = os.getenv(
            "TWSCRAPE_EMAIL_TWO"
        )  # Using TWSCRAPE_EMAIL_TWO for the contact email
        api_key = os.getenv("TWSCRAPE_API_KEY")
        cookies_str = os.getenv("TWSCRAPE_COOKIES")

        if not all([username, password, email, api_key, cookies_str]):
            raise ValueError("Missing required TwScrape environment variables")

        await api.pool.add_account(
            username, password, email, api_key, cookies=cookies_str
        )

        # Search for tweets with improved error handling
        tweets = []
        try:
            async for tweet in api.search(f"{topic}", limit=20):
                tweets.append(tweet.rawContent)
        except Exception as e:
            # Throw exception with a clear message if the search fails
            raise RuntimeError(f"Failed to search tweets for topic '{topic}': {e}")

        # Return tweets as structured data with clear separators
        return {
            "text": "\n\n---TWEET---\n\n".join(tweets),
            "count": len(tweets),
            "topic": topic,
        }


# Global server instance for backwards compatibility
mcp = create_server()

if __name__ == "__main__":
    mcp.run()
