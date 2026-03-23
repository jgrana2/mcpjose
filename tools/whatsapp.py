"""WhatsApp messaging tool(s).

Uses the official WhatsApp Business Platform Cloud API (Meta Graph API).

Notes:
- This requires a WhatsApp Business account/phone number configured in Meta.
"""

from __future__ import annotations

import mimetypes
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from mcp.server.fastmcp import FastMCP
from PIL import Image, ImageOps
from requests import HTTPError
from zoneinfo import ZoneInfo

from core.config import get_config
from core.http_client import HTTPClient
from core.rate_limit import DailyRateLimiter


def _parse_csv_set(value: Optional[str]) -> Set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _normalize_e164ish(number: str) -> str:
    stripped = number.strip()
    if stripped.startswith("+"):
        stripped = stripped[1:]
    stripped = "".join(ch for ch in stripped if ch.isdigit())
    return stripped


WHATSAPP_MAX_IMAGE_BYTES = 500 * 1024


def _prepare_image_for_whatsapp(
    file_path: str,
    mime_type: Optional[str] = None,
    max_bytes: int = WHATSAPP_MAX_IMAGE_BYTES,
) -> tuple[Path, Optional[str], Optional[Path]]:
    path = Path(file_path)
    resolved_mime_type = mime_type or mimetypes.guess_type(path.name)[0]
    if not resolved_mime_type or not resolved_mime_type.startswith("image/"):
        return path, mime_type, None
    if path.stat().st_size <= max_bytes:
        return path, resolved_mime_type, None

    with Image.open(path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        if image.mode not in ("RGB", "L"):
            background = Image.new("RGB", image.size, "white")
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            background.paste(image.convert("RGBA"), mask=alpha)
            image = background
        elif image.mode == "L":
            image = image.convert("RGB")

        current = image
        attempt_settings = [
            (92, 1.0),
            (85, 0.9),
            (78, 0.8),
            (72, 0.7),
            (65, 0.6),
            (58, 0.5),
            (50, 0.4),
        ]

        for quality, scale in attempt_settings:
            candidate = current
            if scale < 1.0:
                next_size = (
                    max(1, int(image.width * scale)),
                    max(1, int(image.height * scale)),
                )
                candidate = image.resize(next_size, Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            candidate.save(temp_path, format="JPEG", quality=quality, optimize=True)
            if temp_path.stat().st_size <= max_bytes:
                return temp_path, "image/jpeg", temp_path
            temp_path.unlink(missing_ok=True)

    raise ValueError(
        f"Image could not be reduced below {max_bytes // 1024} KB for WhatsApp upload: {file_path}"
    )


@dataclass(frozen=True)
class WhatsAppSendResult:
    ok: bool
    destination: str
    provider: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    rate_limit_day: Optional[str] = None
    rate_limit_used: Optional[int] = None
    rate_limit_limit: Optional[int] = None
    rate_limit_remaining: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "ok": self.ok,
            "destination": self.destination,
            "provider": self.provider,
        }
        if self.message_id:
            data["message_id"] = self.message_id
        if self.error:
            data["error"] = self.error
        if self.rate_limit_day is not None:
            data["rate_limit"] = {
                "day": self.rate_limit_day,
                "used": self.rate_limit_used,
                "limit": self.rate_limit_limit,
                "remaining": self.rate_limit_remaining,
            }
        return data


class WhatsAppCloudAPIClient:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str = "v21.0",
        http_client: Optional[HTTPClient] = None,
    ):
        if not access_token:
            raise EnvironmentError("WHATSAPP_ACCESS_TOKEN is not set")
        if not phone_number_id:
            raise EnvironmentError("WHATSAPP_PHONE_NUMBER_ID is not set")
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.http = http_client or HTTPClient()
        self.http.session.headers.update({"Authorization": f"Bearer {access_token}"})

    @property
    def name(self) -> str:
        return "whatsapp_cloud_api"

    def send_text_message(
        self,
        destination: str,
        message: str,
        template_name: Optional[str] = None,
        language_code: str = "en_US",
    ) -> Dict[str, Any]:
        to = _normalize_e164ish(destination)
        if template_name:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": message},
            }
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        try:
            resp = self.http.post(url, json=payload)
        except HTTPError as exc:
            raise RuntimeError(self._format_http_error(exc)) from exc
        return resp.json()

    def upload_media(self, file_path: str, mime_type: Optional[str] = None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        upload_path, upload_mime_type, temp_path = _prepare_image_for_whatsapp(file_path, mime_type)
        if not upload_mime_type:
            upload_mime_type = mimetypes.guess_type(upload_path.name)[0] or "application/octet-stream"
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/media"
        try:
            with upload_path.open("rb") as fh:
                files = {"file": (upload_path.name, fh, upload_mime_type)}
                data = {"messaging_product": "whatsapp", "type": upload_mime_type}
                try:
                    resp = self.http.post(url, data=data, files=files)
                except HTTPError as exc:
                    raise RuntimeError(self._format_http_error(exc)) from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        payload = resp.json()
        media_id = payload.get("id") if isinstance(payload, dict) else None
        if not media_id:
            raise RuntimeError("WhatsApp media upload did not return an id")
        return media_id

    def send_media_message(
        self,
        destination: str,
        media_id: str,
        mime_type: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        to = _normalize_e164ish(destination)
        if mime_type.startswith("image/"):
            msg_type = "image"
        elif mime_type.startswith("video/"):
            msg_type = "video"
        else:
            msg_type = "document"
        media_block: Dict[str, Any] = {"id": media_id}
        if caption:
            media_block["caption"] = caption
        if filename and msg_type == "document":
            media_block["filename"] = filename
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": msg_type,
            msg_type: media_block,
        }
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        try:
            resp = self.http.post(url, json=payload)
        except HTTPError as exc:
            raise RuntimeError(self._format_http_error(exc)) from exc
        return resp.json()

    def _format_http_error(self, error: HTTPError) -> str:
        response = error.response
        if response is None:
            return f"WhatsApp API request failed: {error}"
        details = None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            meta_error = payload.get("error")
            if isinstance(meta_error, dict):
                message = meta_error.get("message")
                code = meta_error.get("code")
                subcode = meta_error.get("error_subcode")
                parts = [part for part in (message, f"code={code}" if code else None) if part]
                if subcode:
                    parts.append(f"subcode={subcode}")
                details = "; ".join(parts)
        if not details:
            body = (response.text or "").strip()
            details = body or str(error)
        return f"WhatsApp API request failed with status {response.status_code}: {details}"


def init_tools(mcp: FastMCP, http_client: Optional[HTTPClient] = None) -> None:
    # Delegate tool behavior to the canonical shared registry implementation.
    from langchain_agent.tool_registry import ProjectToolRegistry

    registry = ProjectToolRegistry()

    @mcp.tool()
    def send_ws_msg(
        destination: Optional[str],
        message: str,
        template_name: Optional[str] = None,
        language_code: Optional[str] = None,
        image_path: Optional[str] = None,
        media_path: Optional[str] = None,
        media_url: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a WhatsApp message or image to a destination number.

        For text messages, provide `destination` and `message`.
        For image messages, additionally provide one of:
          - `image_path` / `media_path`: local file path — the file is uploaded to
            WhatsApp Cloud API and sent as an image; `message` becomes the caption.
          - `media_url`: a public URL to an image — sent directly without uploading.
        Do not provide both a local path and `media_url` at the same time.

        Args:
            destination: E.164-ish phone number (e.g. "+14155550123"). If not provided,
                falls back to the WHATSAPP_DEFAULT_DESTINATION env var.
            message: Text body (required). Used as the image caption for media messages.
            template_name: Optional WhatsApp message template name.
            language_code: Optional language code for template messages (default "en_US").
            image_path: Local image file path to upload and send.
            media_path: Alias for image_path; used when passing non-image media.
            media_url: Public URL to an image to send without uploading.
            mime_type: Optional MIME type override for local uploads.
        """
        return registry.send_ws_msg(
            destination=destination,
            message=message,
            template_name=template_name,
            language_code=language_code,
            image_path=image_path,
            media_path=media_path,
            media_url=media_url,
            mime_type=mime_type,
        )

    @mcp.tool()
    def get_ws_messages(limit: int = 10, since: Optional[str] = None) -> Dict[str, Any]:
        return registry.get_ws_messages(limit=limit, since=since)