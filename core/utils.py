"""Shared utility functions for file handling, image processing, and text manipulation."""

import base64
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

from pdf2image import convert_from_path


# MIME type mappings for common image formats
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def detect_mime_type(file_path: Union[str, Path]) -> str:
    """Detect MIME type based on file extension.

    Args:
        file_path: Path to the file.

    Returns:
        MIME type string, defaults to 'image/png' if unknown.
    """
    ext = Path(file_path).suffix.lower()
    return MIME_TYPES.get(ext, "image/png")


def is_pdf_file(file_path: Union[str, Path]) -> bool:
    """Check if a file path points to a PDF.

    Args:
        file_path: Path to check.

    Returns:
        True if the file has a .pdf extension.
    """
    return Path(file_path).suffix.lower() == ".pdf"


def convert_pdf_to_image(
    pdf_path: Union[str, Path], dpi: int = 400, page_number: int = 1
) -> str:
    """Convert a specific page of a PDF to a temporary PNG image.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for conversion (default: 400 for high quality).
        page_number: Page to convert (1-indexed, default: 1).

    Returns:
        Path to the temporary PNG file.

    Raises:
        RuntimeError: If PDF has no pages or conversion fails.
        FileNotFoundError: If PDF file doesn't exist.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    images = convert_from_path(
        pdf_path, dpi=dpi, first_page=page_number, last_page=page_number
    )
    if not images:
        raise RuntimeError(f"No pages found in PDF or page {page_number} doesn't exist")

    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_file.close()
    images[0].save(temp_file.name, "PNG")
    return temp_file.name


def encode_image_to_data_url(image_path: Union[str, Path]) -> str:
    """Encode an image file to a base64 data URL.

    Args:
        image_path: Path to the image file.

    Returns:
        Data URL string in format "data:{mime_type};base64,{encoded_data}".
    """
    mime_type = detect_mime_type(image_path)
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def load_image_for_processing(
    file_path: Union[str, Path], convert_pdf: bool = True
) -> Tuple[str, Optional[str]]:
    """Load an image file, converting PDF if necessary.

    This is a unified interface for handling both images and PDFs.
    Returns the path to use for processing and an optional temporary file path
    that should be cleaned up after use.

    Args:
        file_path: Path to image or PDF file.
        convert_pdf: Whether to convert PDFs to images (default: True).

    Returns:
        Tuple of (path_to_use, temp_file_path). temp_file_path is None if no
        temporary file was created.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if is_pdf_file(file_path) and convert_pdf:
        temp_path = convert_pdf_to_image(file_path)
        return temp_path, temp_path

    return str(file_path), None


def cleanup_temp_file(temp_path: Optional[str]) -> None:
    """Safely remove a temporary file if it exists.

    Args:
        temp_path: Path to the temporary file, or None.
    """
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)


def build_ocr_prompt(base_prompt: str, ocr_context: Optional[str]) -> str:
    """Build a complete prompt with optional OCR context.

    Args:
        base_prompt: The user's original prompt.
        ocr_context: Optional OCR text detected in the image.

    Returns:
        Combined prompt string.
    """
    if not ocr_context:
        return base_prompt

    return (
        f"OCR Context (text detected in the image):\n"
        f"{ocr_context}\n\n"
        f"User Prompt:\n"
        f"{base_prompt}\n\n"
        f"Please analyze the image using both the visual information "
        f"and the OCR context provided above."
    )


def load_text_file(file_path: Union[str, Path]) -> str:
    """Load text content from a file.

    Args:
        file_path: Path to the text file.

    Returns:
        File contents as string.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_bounding_box(vertices: List) -> Tuple[int, int, int, int]:
    """Extract bounding box coordinates from Vision API vertices.

    Args:
        vertices: List of vertices with x, y attributes.

    Returns:
        Tuple of (x_min, y_min, x_max, y_max).
    """
    x_coords = [v.x for v in vertices]
    y_coords = [v.y for v in vertices]
    return min(x_coords), min(y_coords), max(x_coords), max(y_coords)


def format_search_result(title: str, snippet: str, url: str) -> dict:
    """Standardize search result format across different backends.

    Args:
        title: Result title.
        snippet: Result description/snippet.
        url: Result URL.

    Returns:
        Standardized result dictionary.
    """
    return {
        "title": title or "No title",
        "snippet": snippet or "No description",
        "url": url or "",
    }


def parse_ocr_output(text: str) -> Tuple[List[str], List[List[int]]]:
    """Parse OCR output file format into texts and bounding boxes.

    Args:
        text: OCR output text in format "Text: '...', Box: [x, y, x, y]"

    Returns:
        Tuple of (texts list, boxes list).
    """
    texts, boxes = [], []
    pattern = r"Text: '([^']*)', Box: \[([\d,\s]+)\]"

    for match in re.finditer(pattern, text):
        texts.append(match.group(1))
        coords = list(map(int, match.group(2).split(",")))
        boxes.append(coords)

    return texts, boxes


def clean_text_whitespace(text: str) -> str:
    """Clean excessive whitespace from extracted text.

    Args:
        text: Raw text with potential extra whitespace.

    Returns:
        Cleaned text with normalized line breaks.
    """
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())
