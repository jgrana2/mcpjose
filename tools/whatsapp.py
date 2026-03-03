"""WhatsApp messaging tool(s).

Uses the official WhatsApp Business Platform Cloud API (Meta Graph API).

Notes:
- This requires a WhatsApp Business account/phone number configured in Meta.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from mcp.server.fastmcp import FastMCP
from zoneinfo import ZoneInfo

from core.http_client import HTTPClient
from core.rate_limit import DailyRateLimiter
from core.config import get_config


def _parse_csv_set(value: Optional[str]) -> Set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _normalize_e164ish(number: str) -> str:
    """Best-effort normalization.

    WhatsApp Cloud API expects phone numbers in international format digits,
    typically without '+'.
    """
    stripped = number.strip()
    if stripped.startswith("+"):
        stripped = stripped[1:]
    stripped = "".join(ch for ch in stripped if ch.isdigit())
    return stripped


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
    """Minimal client for Meta WhatsApp Cloud API."""

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
        resp = self.http.post(url, json=payload)
        return resp.json()


def init_tools(mcp: FastMCP, http_client: Optional[HTTPClient] = None) -> None:
    """Register WhatsApp tools."""

    base_http = http_client or HTTPClient()

    repo_root = get_config().repo_root
    limiter = DailyRateLimiter.from_env(
        default_path=Path(repo_root) / "auth" / "rate_limits.sqlite"
    )

    daily_max = int(os.getenv("WHATSAPP_DAILY_MAX", "10"))
    default_destination = os.getenv("WHATSAPP_DEFAULT_DESTINATION")
    tz_name = os.getenv("WHATSAPP_TIMEZONE")
    tz = ZoneInfo(tz_name) if tz_name else datetime.now().astimezone().tzinfo

    @mcp.tool()
    def send_ws_msg(
        destination: Optional[str],
        message: str,
        template_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a WhatsApp message (text or template) using Meta WhatsApp Cloud API.

        Inputs:
            destination: Destination phone number (E.164-ish). If omitted, uses WHATSAPP_DEFAULT_DESTINATION.
            message: Text message body (used for text messages or as fallback).
            template_name: Optional template name for sending template messages (required for new conversations outside 24h window).
            language_code: Optional language code for templates (e.g., 'en_US', defaults to 'en_US').

        Outputs:
            ok: boolean, plus provider info and (if available) message_id.
        """
        dest = (default_destination or "").strip()
        if not dest:
            return WhatsAppSendResult(
                ok=False,
                destination="",
                provider="whatsapp_cloud_api",
                error="Missing predefined destination (set WHATSAPP_DEFAULT_DESTINATION).",
            ).to_dict()

        normalized = _normalize_e164ish(dest)
        if destination:
            requested = _normalize_e164ish(destination)
            if requested and requested != normalized:
                return WhatsAppSendResult(
                    ok=False,
                    destination=normalized,
                    provider="whatsapp_cloud_api",
                    error="Destination is fixed; omit destination or match WHATSAPP_DEFAULT_DESTINATION.",
                ).to_dict()

        if not message or not message.strip():
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error="Message must be a non-empty string.",
            ).to_dict()

        rate = limiter.consume(scope="send_ws_msg", limit=daily_max, amount=1, tz=tz)
        if not rate.allowed:
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error=f"Daily rate limit exceeded for send_ws_msg (max {daily_max}/day).",
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()

        try:
            api = WhatsAppCloudAPIClient(
                access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
                phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
                api_version=os.getenv("WHATSAPP_API_VERSION", "v22.0"),
                http_client=base_http,
            )
            # Use provided template_name, fall back to env var, or None for text messages
            effective_template = template_name or os.getenv("WHATSAPP_TEMPLATE_NAME")
            effective_lang = language_code or os.getenv(
                "WHATSAPP_TEMPLATE_LANGUAGE", "en_US"
            )
            result = api.send_text_message(
                normalized, message.strip(), effective_template, effective_lang
            )
            message_id = None
            if isinstance(result, dict):
                messages = result.get("messages")
                if isinstance(messages, list) and messages:
                    message_id = messages[0].get("id")

            return WhatsAppSendResult(
                ok=True,
                destination=normalized,
                provider=api.name,
                message_id=message_id,
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()
        except Exception as e:
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error=str(e),
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()
