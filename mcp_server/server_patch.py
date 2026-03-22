import os
import logging
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP
from core.guard import SubscriptionGuard

logger = logging.getLogger(__name__)
guard = SubscriptionGuard()

def _get_default_phone_number() -> str:
    """Fallback to the default owner's number if none is provided."""
    num = os.getenv("WHATSAPP_DEFAULT_DESTINATION", "")
    return num.strip().lstrip('+')

def add_guard_to_tools(mcp: FastMCP):
    """
    Wrap specific premium tools with the SubscriptionGuard.
    """
    
    @mcp.tool()
    def premium_action(text: str, phone_number: str = "") -> str:
        """
        A premium action that requires an active subscription.
        If phone_number is not provided, defaults to the server owner.
        """
        
        # 1. Resolve identity
        target_number = phone_number or _get_default_phone_number()
        
        # 2. Guard Check
        access_error = guard.check_access(f"+{target_number}")
        if access_error:
            return access_error
            
        # 3. Actual premium logic
        logger.info(f"Executing premium action for {target_number}: {text}")
        return f"Successfully executed premium action: {text}"
        
