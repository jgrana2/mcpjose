import hashlib
import hmac
import json
import logging
import sqlite3
from typing import Any, Dict, Optional

import mcp.types as types
import requests

from core.config import CredentialManager

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"


class PaymentWebhookTool:
    """Processes MercadoPago webhook events and keeps the subscription DB in sync."""

    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path
        self.creds = CredentialManager()
        self._ensure_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id           TEXT PRIMARY KEY,
                    phone_number TEXT UNIQUE,
                    status       TEXT DEFAULT 'active',
                    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id             TEXT,
                    mp_subscription_id  TEXT PRIMARY KEY,
                    status              TEXT,
                    plan_id             TEXT,
                    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            conn.commit()

    def validate_signature(self, data_id: str, request_id: str, timestamp: str, v1_hash: str) -> bool:
        """Validate x-signature HMAC-SHA256 from MercadoPago webhook headers."""
        secret = self.creds.get_mercadopago_config().get("webhook_secret", "")
        if not secret:
            logger.warning("MP_WEBHOOK_SECRET not set — rejecting webhook signature validation")
            return False

        manifest = f"id:{data_id};request-id:{request_id};ts:{timestamp};"
        expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1_hash)

    def _fetch_preapproval(self, preapproval_id: str) -> Optional[Dict]:
        mp_cfg = self.creds.get_mercadopago_config()
        token = mp_cfg.get("access_token")
        if not token:
            return None
        try:
            resp = requests.get(
                f"{MP_API_BASE}/preapproval/{preapproval_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching preapproval {preapproval_id}: {e}")
            return None

    def _resolve_phone(self, preapproval_id: str, preapproval_data: Optional[Dict]) -> Optional[str]:
        if preapproval_data:
            phone = preapproval_data.get("external_reference")
            if phone:
                return phone
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT phone_number FROM pending_subscriptions WHERE preapproval_id = ?",
                    (preapproval_id,),
                ).fetchone()
            if row:
                return row[0]
        except sqlite3.OperationalError:
            pass
        return None

    def _resolve_plan_id(self, payload: Dict[str, Any], preapproval_data: Optional[Dict], allow_payload_fallbacks: bool) -> str:
        if preapproval_data:
            plan_id = preapproval_data.get("preapproval_plan_id")
            if plan_id:
                return str(plan_id)
        if allow_payload_fallbacks:
            return str(payload.get("plan_id", "default_plan"))
        return "default_plan"

    def process_webhook(
        self,
        payload: Dict[str, Any],
        allow_payload_fallbacks: bool = False,
    ) -> Dict[str, str]:
        event_type = payload.get("type") or payload.get("action")
        if not event_type:
            return {"status": "error", "message": "Missing type/action in payload"}

        data = payload.get("data", {})
        preapproval_id = data.get("id")
        if not preapproval_id:
            return {"status": "error", "message": "Missing preapproval ID in payload data"}

        if event_type not in ("subscription_preapproval", "created", "updated"):
            return {"status": "ignored", "message": f"Event type '{event_type}' not handled"}

        preapproval_data = self._fetch_preapproval(preapproval_id)
        if preapproval_data:
            new_status = preapproval_data.get("status", "authorized")
        else:
            if not allow_payload_fallbacks:
                return {
                    "status": "error",
                    "message": f"Unable to verify preapproval '{preapproval_id}' with MercadoPago",
                }
            new_status = payload.get("status", "authorized")

        phone_number = self._resolve_phone(preapproval_id, preapproval_data)
        if not phone_number and allow_payload_fallbacks:
            phone_number = payload.get("phone_number") or payload.get("user_id", "unknown")
        if not phone_number:
            return {
                "status": "error",
                "message": f"Unable to resolve phone number for preapproval '{preapproval_id}'",
            }

        user_id = (
            payload.get("user_id") if allow_payload_fallbacks else None
        ) or f"mp_{preapproval_id[:12]}"
        plan_id = self._resolve_plan_id(payload, preapproval_data, allow_payload_fallbacks)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM subscriptions WHERE mp_subscription_id = ?",
                    (preapproval_id,),
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        "UPDATE subscriptions SET status = ? WHERE mp_subscription_id = ?",
                        (new_status, preapproval_id),
                    )
                    msg = f"Updated subscription {preapproval_id} → {new_status}"
                else:
                    cursor.execute(
                        "INSERT OR REPLACE INTO users (id, phone_number) VALUES (?, ?)",
                        (user_id, phone_number),
                    )
                    cursor.execute(
                        "INSERT INTO subscriptions (user_id, mp_subscription_id, status, plan_id) VALUES (?, ?, ?, ?)",
                        (user_id, preapproval_id, new_status, plan_id),
                    )
                    msg = f"Created subscription {preapproval_id} for {phone_number} with status {new_status}"

                conn.commit()
                return {"status": "success", "message": msg}
        except sqlite3.Error as e:
            logger.error(f"DB error processing webhook: {e}")
            return {"status": "error", "message": str(e)}

    def create_mcp_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="mp_simulate_webhook",
                description="Simulate a MercadoPago webhook to manually update subscription state (for testing).",
                inputSchema={
                    "type": "object",
                    "properties": {"payload": {"type": "string", "description": "JSON string of the webhook payload"}},
                    "required": ["payload"],
                },
            )
        ]

    async def execute(self, name: str, arguments: dict) -> list[types.TextContent]:
        if name == "mp_simulate_webhook":
            try:
                payload = json.loads(arguments.get("payload", "{}"))
                result = self.process_webhook(payload, allow_payload_fallbacks=True)
                return [types.TextContent(type="text", text=json.dumps(result))]
            except json.JSONDecodeError:
                return [types.TextContent(type="text", text=json.dumps({"error": "Invalid JSON payload"}))]
            except Exception as e:
                return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]

        raise ValueError(f"Unknown tool: {name}")
