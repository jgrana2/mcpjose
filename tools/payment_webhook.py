import json
import logging
import sqlite3
import hmac
import hashlib
from typing import Dict, Any, Optional

import mcp.types as types

from core.config import CredentialManager

logger = logging.getLogger(__name__)

class PaymentWebhookTool:
    """Tool to manually trigger or simulate Mercado Pago webhooks."""

    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path
        self.creds = CredentialManager()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Process a simulated webhook payload."""
        
        event_type = payload.get("action") or payload.get("type")
        
        if not event_type:
            return {"status": "error", "message": "Missing action/type in payload"}

        data = payload.get("data", {})
        sub_id = data.get("id")
        
        if not sub_id:
             return {"status": "error", "message": "Missing subscription ID in payload"}

        if event_type == "created" or event_type == "updated":
            new_status = payload.get("status", "authorized") 
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM subscriptions WHERE mp_subscription_id = ?", (sub_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        cursor.execute(
                            "UPDATE subscriptions SET status = ? WHERE mp_subscription_id = ?",
                            (new_status, sub_id)
                        )
                        msg = f"Updated subscription {sub_id} to {new_status}"
                    else:
                        user_id = payload.get("user_id", "unknown_user")
                        phone_number = payload.get("phone_number", user_id) # USE THE REAL PHONE NUMBER
                        
                        cursor.execute(
                            "INSERT OR REPLACE INTO users (id, phone_number) VALUES (?, ?)",
                            (user_id, phone_number)
                        )
                        cursor.execute(
                            "INSERT INTO subscriptions (user_id, mp_subscription_id, status, plan_id) VALUES (?, ?, ?, ?)",
                            (user_id, sub_id, new_status, "default_plan")
                        )
                        msg = f"Created new subscription {sub_id} for user {user_id} with status {new_status}"
                    
                    conn.commit()
                    return {"status": "success", "message": msg}
            except sqlite3.Error as e:
                logger.error(f"Database error processing webhook: {e}")
                return {"status": "error", "message": str(e)}
                
        return {"status": "ignored", "message": f"Event type {event_type} ignored"}

    # ... rest of the class remains same (create_mcp_tools, execute)
    def create_mcp_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="mp_simulate_webhook",
                description="Simulate an incoming Mercado Pago webhook to update subscription state.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payload": {
                            "type": "string", 
                            "description": "JSON string of the webhook payload"
                        }
                    },
                    "required": ["payload"]
                }
            )
        ]

    async def execute(self, name: str, arguments: dict) -> list[types.TextContent]:
        if name == "mp_simulate_webhook":
            try:
                payload_str = arguments.get("payload", "{}")
                payload = json.loads(payload_str)
                result = self.process_webhook(payload)
                return [types.TextContent(type="text", text=json.dumps(result))]
            except json.JSONDecodeError:
                return [types.TextContent(type="text", text=json.dumps({"error": "Invalid JSON payload"}))]
            except Exception as e:
                return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
        
        raise ValueError(f"Unknown tool: {name}")

