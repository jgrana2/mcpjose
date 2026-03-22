import asyncio
import json
import logging
import os
import sqlite3
from typing import Any, Dict, Optional

import mcp.types as types
import requests

from core.config import CredentialManager

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"


class PaymentGatewayTool:
    """MercadoPago Subscriptions — creates checkout links and queries subscription state."""

    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path
        self.creds = CredentialManager()
        self._ensure_tables()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        """Create pending_subscriptions table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_subscriptions (
                    preapproval_id TEXT PRIMARY KEY,
                    phone_number   TEXT NOT NULL,
                    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _store_pending(self, preapproval_id: str, phone_number: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_subscriptions (preapproval_id, phone_number) VALUES (?, ?)",
                (preapproval_id, phone_number),
            )
            conn.commit()

    def lookup_pending_phone(self, preapproval_id: str) -> Optional[str]:
        """Return the phone number stored for a pending preapproval, if any."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT phone_number FROM pending_subscriptions WHERE preapproval_id = ?",
                (preapproval_id,),
            ).fetchone()
        return row[0] if row else None

    # ------------------------------------------------------------------
    # MP API helpers
    # ------------------------------------------------------------------

    def _get_headers(self) -> Dict[str, str]:
        access_token = self.creds.get_api_key("mercadopago")
        if not access_token:
            logger.warning("MP_ACCESS_TOKEN not configured.")
            return {}
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _mp_post(self, path: str, body: Dict) -> Dict:
        headers = self._get_headers()
        if not headers:
            return {"error": "MP_ACCESS_TOKEN not configured"}
        resp = requests.post(f"{MP_API_BASE}{path}", json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _mp_get(self, path: str) -> Dict:
        headers = self._get_headers()
        if not headers:
            return {"error": "MP_ACCESS_TOKEN not configured"}
        resp = requests.get(f"{MP_API_BASE}{path}", headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _mp_put(self, path: str, body: Dict) -> Dict:
        headers = self._get_headers()
        if not headers:
            return {"error": "MP_ACCESS_TOKEN not configured"}
        resp = requests.put(f"{MP_API_BASE}{path}", json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Core actions
    # ------------------------------------------------------------------

    def create_checkout_link(self, phone_number: str, payer_email: Optional[str] = None) -> Dict[str, Any]:
        """Create a MercadoPago subscription (preapproval) and return the init_point URL.

        The phone_number is stored as external_reference so the webhook can map
        the payment back to the user without needing it in the webhook payload.
        """
        mp_cfg = self.creds.get_mercadopago_config()
        payer_email = payer_email or mp_cfg.get("payer_email") or os.getenv("MP_PAYER_EMAIL")

        if not payer_email:
            return {
                "error": "Missing payer email. Set MP_PAYER_EMAIL in auth/.env or config."
            }

        body = {
            "reason": mp_cfg["plan_reason"],
            "external_reference": phone_number,
            "back_url": mp_cfg["back_url"],
            "payer_email": payer_email,
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": mp_cfg["plan_amount"],
                "currency_id": mp_cfg["currency"],
            },
        }

        try:
            result = self._mp_post("/preapproval", body)
            preapproval_id = result.get("id")
            init_point = result.get("init_point")

            if preapproval_id:
                self._store_pending(preapproval_id, phone_number)

            return {
                "init_point": init_point,
                "preapproval_id": preapproval_id,
                "status": result.get("status"),
            }
        except requests.HTTPError as e:
            logger.error(f"MP API error creating checkout link: {e.response.text}")
            return {"error": f"MP API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error creating checkout link: {e}")
            return {"error": str(e)}

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a specific preapproval subscription."""
        try:
            return await asyncio.to_thread(self._mp_get, f"/preapproval/{subscription_id}")
        except Exception as e:
            logger.error(f"Error fetching MP subscription {subscription_id}: {e}")
            return None

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a MercadoPago preapproval subscription by id."""
        try:
            result = self._mp_put(f"/preapproval/{subscription_id}", {"status": "cancelled"})
            return {
                "preapproval_id": result.get("id", subscription_id),
                "status": result.get("status", "cancelled"),
            }
        except requests.HTTPError as e:
            logger.error(f"MP API error cancelling subscription: {e.response.text}")
            return {"error": f"MP API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error cancelling subscription: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # MCP tool registration
    # ------------------------------------------------------------------

    def create_mcp_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="mp_create_checkout_link",
                description=(
                    "Generate a MercadoPago Checkout Pro subscription link for a user. "
                    "Returns an init_point URL the user can open to complete payment."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "phone_number": {
                            "type": "string",
                            "description": "User's phone number (E.164 format, e.g. +5491112345678)",
                        },
                        "payer_email": {
                            "type": "string",
                            "description": "Buyer email for this subscription (recommended for multi-account flows)",
                        },
                    },
                    "required": ["phone_number"],
                },
            ),
            types.Tool(
                name="mp_check_subscription",
                description="Check the current status of a MercadoPago subscription by preapproval ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {
                            "type": "string",
                            "description": "The MercadoPago preapproval ID",
                        }
                    },
                    "required": ["subscription_id"],
                },
            ),
            types.Tool(
                name="mp_cancel_subscription",
                description="Cancel a MercadoPago subscription (preapproval) by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {
                            "type": "string",
                            "description": "The MercadoPago preapproval ID to cancel",
                        }
                    },
                    "required": ["subscription_id"],
                },
            ),
        ]

    async def execute(self, name: str, arguments: dict) -> list[types.TextContent]:
        if name == "mp_create_checkout_link":
            phone = arguments.get("phone_number", "")
            payer_email = arguments.get("payer_email")
            result = self.create_checkout_link(phone, payer_email=payer_email)
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "mp_check_subscription":
            sub_id = arguments.get("subscription_id")
            result = await self.get_subscription(sub_id)
            if result:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"status": result.get("status"), "reason": result.get("reason")}),
                )]
            return [types.TextContent(type="text", text=json.dumps({"error": "Failed to fetch subscription"}))]

        if name == "mp_cancel_subscription":
            sub_id = arguments.get("subscription_id", "")
            result = self.cancel_subscription(sub_id)
            return [types.TextContent(type="text", text=json.dumps(result))]

        raise ValueError(f"Unknown tool: {name}")

