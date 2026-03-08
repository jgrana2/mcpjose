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
from tools.whatsapp import init_tools as init_whatsapp_tools
from tools.wolfram_alpha import init_tools as init_wolfram_alpha_tools


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tools.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP("mcpjose")

    # Initialize navigation tools
    init_navigation_tools(mcp)

    # Initialize WhatsApp tools
    init_whatsapp_tools(mcp)

    # Initialize search tools
    _init_search_tools(mcp)

    # Initialize Wolfram Alpha tools
    init_wolfram_alpha_tools(mcp)

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
        transcription = ProviderFactory.create_transcription("openai")
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI transcription: {e}")

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

    if transcription:

        @mcp.tool()
        def transcribe_audio(
            audio_path: str,
            model: str = "gpt-4o-transcribe",
            language: Optional[str] = None,
            response_format: str = "text",
            timestamp_granularities: Optional[List[str]] = None,
            prompt: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Transcribe audio file to text using OpenAI Whisper.

            Args:
                audio_path: Path to audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm).
                model: Model to use (gpt-4o-transcribe, gpt-4o-mini-transcribe, whisper-1).
                language: ISO language code for the audio (e.g., 'en', 'es').
                response_format: Output format (text, json, verbose_json, srt, vtt).
                timestamp_granularities: List of timestamp granularities (['word'], ['segment']).
                prompt: Optional context hint to improve transcription accuracy.

            Returns:
                Dictionary with transcription result. Format varies by response_format:
                - text: {"text": "transcription"}
                - json/verbose_json: {"text": "...", "duration": ..., "language": "..."}
                - With timestamps: includes "words" or "segments" arrays
            """
            try:
                # Build kwargs for API call
                kwargs = {"model": model, "response_format": response_format}
                if language:
                    kwargs["language"] = language
                if timestamp_granularities:
                    kwargs["timestamp_granularities"] = timestamp_granularities
                if prompt:
                    kwargs["prompt"] = prompt

                # Call transcription provider
                result = transcription.transcribe(audio_path, **kwargs)

                # Handle different response formats
                if response_format == "text":
                    # Plain text response
                    return {"text": result if isinstance(result, str) else result.text}
                else:
                    # Structured response (json, verbose_json, etc.)
                    # Convert to dict if needed
                    if hasattr(result, "model_dump"):
                        return result.model_dump()
                    elif hasattr(result, "dict"):
                        return result.dict()
                    else:
                        return {"result": str(result)}

            except FileNotFoundError as e:
                return {"error": str(e)}
            except ValueError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": f"Transcription failed: {str(e)}"}

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

        IMPORTANT: X (Twitter) uses DETERMINISTIC keyword matching, not heuristic search.
        For best results, use SHORT, SPECIFIC keywords (max 3 words recommended).
        The tool automatically extracts up to 3 key words from longer queries.
        
        Examples of good queries:
        - "AI agents" (2 words)
        - "climate change technology" (3 words)
        - "Python FastAPI" (2 words)
        
        Avoid: Long sentences, common words, or overly generic terms.

        Args:
            topic: The search topic/query (will be optimized to max 3 keywords)

        Returns:
            Dictionary with 'text' (concatenated tweets), 'count' (int), 'topic', and 'search_query'
        """
        
        # Common stop words to filter out for better keyword extraction
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'about', 'how', 'what', 'when', 'where',
            'who', 'why', 'which', 'de', 'para', 'con', 'sin', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas'
        }
        
        # Extract keywords: remove stop words and keep max 3 meaningful words
        words = topic.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2][:3]
        
        # If no keywords remain after filtering, use first 3 words of original
        if not keywords:
            keywords = words[:3]
        
        search_query = " ".join(keywords)

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
            async for tweet in api.search(search_query, limit=20):
                tweets.append(tweet.rawContent)
        except Exception as e:
            # Throw exception with a clear message if the search fails
            raise RuntimeError(f"Failed to search tweets for topic '{topic}': {e}")

        # Return tweets as structured data with clear separators
        return {
            "text": "\n\n---POST---\n\n".join(tweets),
            "count": len(tweets),
            "topic": topic,
            "search_query": search_query,
        }


# Global server instance for backwards compatibility
mcp = create_server()

if __name__ == "__main__":
    mcp.run()
