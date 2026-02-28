"""Concrete implementations of AI service providers."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.cloud import vision as google_vision
from google.oauth2 import service_account
from google import genai as google_genai
from google.genai import types as genai_types
from openai import OpenAI
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from core.config import CredentialManager
from core.interfaces import (
    ImageGenerator,
    LLMProvider,
    OCRProvider,
    VisionProvider,
)
from core import utils
from core.utils import (
    build_ocr_prompt,
    cleanup_temp_file,
    encode_image_to_data_url,
    extract_bounding_box,
    load_image_for_processing,
    load_text_file,
    detect_mime_type,
)


class OpenAIClient:
    """Lazy-initialized OpenAI client singleton."""

    _instance: Optional[OpenAI] = None

    @classmethod
    def get(cls) -> OpenAI:
        if cls._instance is None:
            CredentialManager().ensure_openai_key()
            cls._instance = OpenAI()
        return cls._instance


class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-4 Vision implementation."""

    DEFAULT_MODEL = "gpt-5-mini"

    def __init__(self, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAIClient.get()
        return self._client

    def process_image(
        self,
        image_path: Union[str, Path],
        prompt: str,
        ocr_context: Optional[str] = None,
        **kwargs,
    ) -> str:
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        temp_path = None
        try:
            # Handle PDF conversion if needed
            image_to_send, temp_path = load_image_for_processing(image_path)
            image_data_url = encode_image_to_data_url(image_to_send)

            complete_prompt = build_ocr_prompt(prompt, ocr_context)

            response = self.client.responses.create(
                model=kwargs.get("model", self.model),
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": complete_prompt},
                            {"type": "input_image", "image_url": image_data_url},
                        ],
                    }
                ],
            )
            return response.output_text
        finally:
            cleanup_temp_file(temp_path)


class GeminiVisionProvider(VisionProvider):
    """Google Gemini multimodal implementation."""

    DEFAULT_MODEL = "gemini-3-flash-preview"

    def __init__(self, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self._init_vertex()

    def _init_vertex(self) -> None:
        """Initialize Vertex AI with credentials."""
        creds = CredentialManager().ensure_google_credentials()
        credentials = service_account.Credentials.from_service_account_file(
            creds["credentials_path"]
        )
        vertexai.init(
            project=creds["project_id"], location="us-central1", credentials=credentials
        )

    @property
    def name(self) -> str:
        return "gemini"

    def process_image(
        self,
        image_path: Union[str, Path],
        prompt: str,
        ocr_context: Optional[str] = None,
        **kwargs,
    ) -> str:
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        temp_path = None
        try:
            # Handle PDF conversion if needed
            image_to_send, temp_path = load_image_for_processing(image_path)

            with open(image_to_send, "rb") as f:
                image_bytes = f.read()

            image_part = Part.from_data(
                data=image_bytes, mime_type=detect_mime_type(image_to_send)
            )

            complete_prompt = build_ocr_prompt(prompt, ocr_context)

            model = GenerativeModel(kwargs.get("model", self.model))
            response = model.generate_content([complete_prompt, image_part])
            return response.text or ""
        finally:
            cleanup_temp_file(temp_path)


class OpenAILLMProvider(LLMProvider):
    """OpenAI text completion provider."""

    DEFAULT_MODEL = "gpt-5-mini"

    def __init__(self, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAIClient.get()
        return self._client

    def complete(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


class GeminiImageGenerator(ImageGenerator):
    """Google Gemini image generation provider."""

    DEFAULT_MODEL = "gemini-3-pro-image-preview"

    def __init__(self):
        self._client = None

    def _init_client(self) -> None:
        """Lazy initialization of the GenAI client."""
        if self._client is None:
            self._client = google_genai.Client()

    @property
    def name(self) -> str:
        return "gemini"

    def generate(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._init_client()

        # Build contents: image + text if image_path provided, text only otherwise
        if image_path:
            from PIL import Image

            image = Image.open(image_path)
            contents = [prompt, image]
        else:
            contents = prompt

        response = self._client.models.generate_content(
            model=self.DEFAULT_MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                image_config=genai_types.ImageConfig(
                    aspect_ratio="16:9", image_size="4K"
                ),
            ),
        )

        result: Dict[str, Any] = {}
        image_parts = [part for part in response.parts if part.inline_data]

        if image_parts:
            image = image_parts[0].as_image()
            save_path = output_path or "generated_image.png"
            image.save(save_path)
            result["image_path"] = save_path

        # Also capture any text response
        text_parts = [part for part in response.parts if part.text]
        if text_parts:
            result["text"] = text_parts[0].text

        return result


class GoogleOCRProvider(OCRProvider):
    """Google Cloud Vision OCR provider."""

    def __init__(self):
        self._client: Optional[google_vision.ImageAnnotatorClient] = None

    @property
    def name(self) -> str:
        return "google"

    @property
    def client(self) -> google_vision.ImageAnnotatorClient:
        if self._client is None:
            # Ensure credentials are set
            CredentialManager().ensure_google_credentials()
            self._client = google_vision.ImageAnnotatorClient()
        return self._client

    def extract_text(
        self, file_path: Union[str, Path], file_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        file_path = Path(file_path)

        if not file_type:
            file_type = "pdf" if file_path.suffix.lower() == ".pdf" else "image"

        if file_type == "pdf":
            return self._extract_from_pdf(file_path)
        else:
            return self._extract_from_image(file_path)

    def _extract_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF using per-page image conversion."""
        from pdf2image import convert_from_path
        import io

        images = convert_from_path(str(pdf_path), dpi=300)
        annotations: List[Dict[str, Any]] = []

        for page_num, image in enumerate(images, 1):
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="PNG")

            response = self.client.document_text_detection(
                image=google_vision.Image(content=img_bytes.getvalue())
            )

            annotations.extend(self._parse_annotations(response, page_num))

        return annotations

    def _extract_from_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """Extract text from a single image."""
        with open(image_path, "rb") as f:
            content = f.read()

        response = self.client.document_text_detection(
            image=google_vision.Image(content=content)
        )

        return self._parse_annotations(response, page=1)

    def _parse_annotations(
        self, response: google_vision.AnnotateImageResponse, page: int
    ) -> List[Dict[str, Any]]:
        """Parse Vision API response into standardized format."""
        annotations: List[Dict[str, Any]] = []

        if not response.text_annotations:
            return annotations

        # Skip first annotation (full text), process individual elements
        for annotation in response.text_annotations[1:]:
            if annotation.bounding_poly and annotation.bounding_poly.vertices:
                x_min, y_min, x_max, y_max = extract_bounding_box(
                    annotation.bounding_poly.vertices
                )
                annotations.append(
                    {
                        "text": annotation.description,
                        "box": [x_min, y_min, x_max, y_max],
                        "page": page,
                    }
                )

        return annotations

    def save_annotations(
        self, annotations: List[Dict[str, Any]], output_path: Union[str, Path]
    ) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            for item in annotations:
                f.write(f"Text: '{item['text']}', Box: {item['box']}\n")


# Provider factory for easy instantiation
class ProviderFactory:
    """Factory for creating provider instances based on type."""

    _vision_providers = {
        "openai": OpenAIVisionProvider,
        "gemini": GeminiVisionProvider,
    }

    _llm_providers = {
        "openai": OpenAILLMProvider,
    }

    _image_generators = {
        "gemini": GeminiImageGenerator,
    }

    _ocr_providers = {
        "google": GoogleOCRProvider,
    }

    @classmethod
    def create_vision(cls, provider: str = "openai", **kwargs) -> VisionProvider:
        if provider not in cls._vision_providers:
            raise ValueError(f"Unknown vision provider: {provider}")
        return cls._vision_providers[provider](**kwargs)

    @classmethod
    def create_llm(cls, provider: str = "openai", **kwargs) -> LLMProvider:
        if provider not in cls._llm_providers:
            raise ValueError(f"Unknown LLM provider: {provider}")
        return cls._llm_providers[provider](**kwargs)

    @classmethod
    def create_image_generator(
        cls, provider: str = "gemini", **kwargs
    ) -> ImageGenerator:
        if provider not in cls._image_generators:
            raise ValueError(f"Unknown image generator: {provider}")
        return cls._image_generators[provider](**kwargs)

    @classmethod
    def create_ocr(cls, provider: str = "google", **kwargs) -> OCRProvider:
        if provider not in cls._ocr_providers:
            raise ValueError(f"Unknown OCR provider: {provider}")
        return cls._ocr_providers[provider](**kwargs)
