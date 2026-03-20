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
from typing import Any, Dict, List, Optional, Set

from mcp.server.fastmcp import FastMCP
from requests import HTTPError
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


@dataclass(frozen=True)
class WhatsAppMessage:
    id: str
    from_number: str
    timestamp: str
    type: str
    body: Optional[str] = None
    caption: Optional[str] = None
    media_id: Optional[str] = None
    media_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "from": self.from_number,
            "timestamp": self.timestamp,
            "type": self.type,
        }
        if self.body:
            data["body"] = self.body
        if self.caption:
            data["caption"] = self.caption
        if self.media_id:
            data["media_id"] = self.media_id
        if self.media_type:
            data["media_type"] = self.media_type
        return data


@dataclass(frozen=True)
class WhatsAppMessagesResult:
    ok: bool
    provider: str
    messages: List[WhatsAppMessage]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "messages": [m.to_dict() for m in self.messages],
            "error": self.error,
        }


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

        return (
            f"WhatsApp API request failed with status {response.status_code}: {details}"
        )


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
        # Determine destination to use
        if destination:
            # Use the destination provided by the user
            normalized = _normalize_e164ish(destination)
        else:
            # Use default destination if none provided
            dest = (default_destination or "").strip()
            if not dest:
                return WhatsAppSendResult(
                    ok=False,
                    destination="",
                    provider="whatsapp_cloud_api",
                    error="Missing destination. Provide a destination or set WHATSAPP_DEFAULT_DESTINATION.",
                ).to_dict()
            normalized = _normalize_e164ish(dest)

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

    @mcp.tool()
    def get_ws_messages(
        limit: int = 10,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch recent WhatsApp messages received via webhook.

        Retrieves messages stored from incoming webhook events. Requires the
        webhook server to be running and Meta webhook to be configured.

        Args:
            limit: Maximum number of messages to fetch (default 10).
            since: Optional timestamp (ISO 8601) to fetch messages after.

        Returns:
            Dictionary with:
                ok: boolean indicating success
                messages: list of message objects with id, from, timestamp, type, body, etc.
                count: number of messages returned

        Note:
            - Run webhook server: python -m tools.whatsapp_webhook
            - Configure webhook URL in Meta Developer dashboard
            - Messages stored locally in SQLite database
        """
        try:
            from tools.whatsapp_webhook import get_message_store

            store = get_message_store()
            messages = store.get_recent(limit=limit, since=since)

            return {
                "ok": True,
                "messages": [m.to_dict() for m in messages],
                "count": len(messages),
            }
        except Exception as e:
            return {
                "ok": False,
                "messages": [],
                "count": 0,
                "error": str(e),
            }
