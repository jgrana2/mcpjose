import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SubscriptionGuard:
    """Validates user subscriptions before allowing agent tasks."""
    
    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def is_authorized(self, phone_number: str) -> bool:
        """
        Check if a user has an active subscription.
        Returns True if authorized, False otherwise.
        """
        import os
        from dotenv import load_dotenv

        # Ensure env is loaded because auth/.env might have WHATSAPP_DEFAULT_DESTINATION
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)

        default_dest = os.getenv("WHATSAPP_DEFAULT_DESTINATION", "").strip()
        
        # Normalize to digit-only string for robust comparison
        clean_phone = "".join(ch for ch in phone_number if ch.isdigit())
        clean_default = "".join(ch for ch in default_dest if ch.isdigit())
        
        # The owner/default destination should always be authorized to use premium tools
        if clean_default and clean_phone == clean_default:
            return True

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Join users and subscriptions to check status
                cursor.execute("""
                    SELECT s.status 
                    FROM users u
                    JOIN subscriptions s ON u.id = s.user_id
                    WHERE u.phone_number IN (?, ?, ?)
                """, (phone_number, clean_phone, f"+{clean_phone}"))
                
                row = cursor.fetchone()
                
                if row and row[0] == 'authorized':
                    return True
                return False
                
        except sqlite3.Error as e:
            logger.error(f"Database error in SubscriptionGuard: {e}")
            return False

    def check_access(self, phone_number: str) -> str:
        """
        Returns an empty string if access is allowed, 
        or an error message if access is denied.
        """
        if self.is_authorized(phone_number):
            return ""
        
        return "Access Denied: You do not have an active subscription. Please renew your plan to continue using premium features."
