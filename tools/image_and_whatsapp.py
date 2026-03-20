"""Combined image generation and WhatsApp sending tool."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from providers import ProviderFactory
from tools.whatsapp import WhatsAppCloudAPIClient, _normalize_e164ish


def init_tools(mcp: FastMCP) -> None:
    """Register combined image generation and WhatsApp tools."""

    try:
        image_gen = ProviderFactory.create_image_generator("gemini")
    except Exception:
        image_gen = None

    @mcp.tool()
    def generate_and_send_image(
        prompt: str,
        destination: Optional[str] = None,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an image and send it over WhatsApp as a real media message."""
        if image_gen is None:
            return {"ok": False, "error": "Image generator is unavailable."}

        gen_result = image_gen.generate(prompt, output_path, image_path)
        saved_path = gen_result.get("image_path")
        if not saved_path:
            return {
                "ok": False,
                "generation": gen_result,
                "error": "Image generation did not return an image_path.",
            }

        dest = destination or os.getenv("WHATSAPP_DEFAULT_DESTINATION")
        if not dest:
            return {
                "ok": False,
                "generation": gen_result,
                "error": "Missing destination. Provide a destination or set WHATSAPP_DEFAULT_DESTINATION.",
            }

        normalized_destination = _normalize_e164ish(dest)
        caption = message or gen_result.get("text") or "Generated image"
        if not caption.strip():
            caption = "Generated image"

        try:
            api = WhatsAppCloudAPIClient(
                access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
                phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
                api_version=os.getenv("WHATSAPP_API_VERSION", "v22.0"),
            )
            mime_type = mimetypes.guess_type(saved_path)[0] or "image/png"
            media_id = api.upload_media(saved_path, mime_type=mime_type)
            result = api.send_image_message(
                normalized_destination,
                media_id=media_id,
                caption=caption,
            )
            return {
                "ok": True,
                "generation": gen_result,
                "media_id": media_id,
                "send": result,
            }
        except Exception as e:
            return {"ok": False, "generation": gen_result, "error": str(e)}
