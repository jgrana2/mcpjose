"""Abstract base classes and protocols for AI service providers.

Implements SOLID principles:
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Tools depend on abstractions, not concrete implementations
- Open/Closed: New providers can be added without modifying existing code
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union
from pathlib import Path


class VisionProvider(ABC):
    """Abstract base class for vision/language model providers.

    Provides a unified interface for processing images with text prompts
    across different AI providers (OpenAI, Gemini, etc.).
    """

    @abstractmethod
    def process_image(
        self,
        image_path: Union[str, Path],
        prompt: str,
        ocr_context: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Process an image with a text prompt.

        Args:
            image_path: Path to the image file.
            prompt: Text prompt to send to the model.
            ocr_context: Optional OCR context to include.
            **kwargs: Provider-specific parameters.

        Returns:
            Model response as string.

        Raises:
            FileNotFoundError: If image file doesn't exist.
            RuntimeError: If processing fails.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass


class ImageGenerator(ABC):
    """Abstract base class for image generation providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate.
            output_path: Optional path to save the generated image.
            image_path: Optional path to an input image for image-to-image generation.

        Returns:
            Dictionary with 'text' and/or 'image_path' keys.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass


class OCRProvider(ABC):
    """Abstract base class for OCR (Optical Character Recognition) providers."""

    @abstractmethod
    def extract_text(
        self, file_path: Union[str, Path], file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract text and bounding boxes from an image or PDF.

        Args:
            file_path: Path to the file to process.
            file_type: Optional file type hint ('pdf' or 'image').

        Returns:
            List of annotation dictionaries with 'text', 'box', and 'page' keys.
        """
        pass

    @abstractmethod
    def save_annotations(
        self, annotations: List[Dict[str, Any]], output_path: Union[str, Path]
    ) -> None:
        """Save annotations to a file.

        Args:
            annotations: List of annotation dictionaries.
            output_path: Path to save the output.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass


class SearchProvider(Protocol):
    """Protocol for search providers (structural subtyping).

    Using Protocol allows any class with these methods to be used
    as a search provider without explicit inheritance.
    """

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute a search query.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            Dictionary with 'results' key containing list of results.
        """
        ...

    @property
    def name(self) -> str:
        """Return the provider name."""
        ...


class LLMProvider(ABC):
    """Abstract base class for text-based LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """Generate a text completion for the given prompt.

        Args:
            prompt: Input prompt text.
            **kwargs: Provider-specific parameters.

        Returns:
            Generated text response.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
