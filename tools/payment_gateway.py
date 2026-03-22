import json
import logging
from typing import Dict, Any, Optional

import mcp.types as types

from core.config import CredentialManager
from core.http_client import HTTPClient

logger = logging.getLogger(__name__)

class PaymentGatewayTool:
    """Tool for interacting with Mercado Pago Subscriptions API."""

    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client
        self.creds = CredentialManager()
        self.base_url = "https://api.mercadopago.com"

    def _get_headers(self) -> Dict[str, str]:
        """Get the required headers for Mercado Pago API requests."""
        access_token = self.creds.get_api_key("mercadopago")
        if not access_token:
            logger.warning("Mercado Pago access token not found in credentials.")
            return {}

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a specific subscription."""
        headers = self._get_headers()
        if not headers:
            return None

        url = f"{self.base_url}/preapproval/{subscription_id}"
        
        try:
            # We use the synchronous HTTPClient inside an async wrapper
            import asyncio
            response = await asyncio.to_thread(self.http_client.get, url, headers=headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Mercado Pago subscription {subscription_id}: {e}")
            return None

    def create_mcp_tools(self) -> list[types.Tool]:
        """Register tools with the MCP server. Keeping it minimal for now."""
        return [
            types.Tool(
                name="mp_check_subscription",
                description="Check the current status of a Mercado Pago subscription by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {"type": "string", "description": "The Mercado Pago preapproval ID"}
                    },
                    "required": ["subscription_id"]
                }
            )
        ]

    async def execute(self, name: str, arguments: dict) -> list[types.TextContent]:
        """Execute the requested tool."""
        if name == "mp_check_subscription":
            sub_id = arguments.get("subscription_id")
            result = await self.get_subscription(sub_id)
            if result:
                return [types.TextContent(type="text", text=json.dumps({"status": result.get("status"), "reason": result.get("reason")}))]
            return [types.TextContent(type="text", text=json.dumps({"error": "Failed to fetch subscription"}))]
        
        raise ValueError(f"Unknown tool: {name}")
