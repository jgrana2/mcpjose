"""Minimal WhatsApp webhook handler.

Stores incoming messages in SQLite for retrieval via get_ws_messages tool.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from flask import Flask, jsonify, request
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    Flask = None  # type: ignore[assignment]
    jsonify = None  # type: ignore[assignment]
    request = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredMessage:
    """Represents a stored WhatsApp message."""

    id: str
    from_number: str
    timestamp: str
    type: str
    body: Optional[str] = None
    caption: Optional[str] = None
    media_id: Optional[str] = None
    media_type: Optional[str] = None
    received_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_number,
            "timestamp": self.timestamp,
            "type": self.type,
            "body": self.body,
            "caption": self.caption,
            "media_id": self.media_id,
            "media_type": self.media_type,
            "received_at": self.received_at,
        }


class MessageStore:
    """SQLite-backed message storage."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create messages table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id TEXT PRIMARY KEY,
                    from_number TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    body TEXT,
                    caption TEXT,
                    media_id TEXT,
                    media_type TEXT,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON whatsapp_messages(timestamp DESC)
            """)

    def add(self, message: StoredMessage) -> None:
        """Store a message."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO whatsapp_messages 
                (id, from_number, timestamp, type, body, caption, media_id, media_type, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.from_number,
                    message.timestamp,
                    message.type,
                    message.body,
                    message.caption,
                    message.media_id,
                    message.media_type,
                    message.received_at or datetime.now().isoformat(),
                ),
            )

    def get_recent(
        self, limit: int = 10, since: Optional[str] = None
    ) -> List[StoredMessage]:
        """Retrieve recent messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if since:
                rows = conn.execute(
                    """
                    SELECT * FROM whatsapp_messages 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (since, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM whatsapp_messages 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            return [
                StoredMessage(
                    id=row["id"],
                    from_number=row["from_number"],
                    timestamp=row["timestamp"],
                    type=row["type"],
                    body=row["body"],
                    caption=row["caption"],
                    media_id=row["media_id"],
                    media_type=row["media_type"],
                    received_at=row["received_at"],
                )
                for row in rows
            ]


def extract_message(data: Dict[str, Any]) -> Optional[StoredMessage]:
    """Extract message from webhook payload."""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        if "messages" not in value:
            return None

        msg = value["messages"][0]
        msg_type = msg.get("type", "unknown")

        body = None
        caption = None
        media_id = None
        media_type = None

        if msg_type == "text":
            body = msg.get("text", {}).get("body")
        elif msg_type in ("image", "video", "audio", "document"):
            media_type = msg_type
            media_id = msg.get(msg_type, {}).get("id")
            caption = msg.get(msg_type, {}).get("caption")
        elif msg_type == "location":
            body = f"Location: {msg.get('location', {})}"
        elif msg_type == "contacts":
            body = f"Contacts: {msg.get('contacts', [])}"

        return StoredMessage(
            id=msg.get("id", ""),
            from_number=msg.get("from", ""),
            timestamp=msg.get("timestamp", ""),
            type=msg_type,
            body=body,
            caption=caption,
            media_id=media_id,
            media_type=media_type,
        )
    except (KeyError, IndexError) as e:
        logger.warning(f"Failed to extract message: {e}")
        return None


def create_webhook_app(db_path: Optional[Path] = None) -> Flask:
    """Create Flask app for WhatsApp webhook."""
    if Flask is None or jsonify is None or request is None:
        raise ImportError(
            "Flask is required to run the WhatsApp webhook server."
        )

    app = Flask(__name__)

    # Use same db directory as rate limiter
    if db_path is None:
        from core.config import get_config

        repo_root = get_config().repo_root
        db_path = Path(repo_root) / "auth" / "whatsapp_messages.sqlite"

    store = MessageStore(db_path)
    verify_token = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")

    @app.route("/webhook", methods=["GET"])
    def verify():
        """Handle webhook verification from Meta."""
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verified")
            return challenge, 200
        return "Forbidden", 403

    @app.route("/webhook", methods=["POST"])
    def receive():
        """Handle incoming webhook events."""
        # Verify signature if app secret is configured
        if app_secret:
            signature = request.headers.get("X-Hub-Signature-256", "")
            expected = (
                "sha256="
                + hmac.new(
                    app_secret.encode(),
                    request.data,
                    hashlib.sha256,
                ).hexdigest()
            )
            if not hmac.compare_digest(signature, expected):
                return "Unauthorized", 401

        try:
            data = request.get_json()
            message = extract_message(data)

            if message:
                store.add(message)
                logger.info(f"Stored message from {message.from_number}")

            return jsonify({"status": "ok"}), 200
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200

    return app


def run_webhook_server(
    host: str = "0.0.0.0", port: int = 5000, db_path: Optional[Path] = None
) -> None:
    """Run the webhook server."""
    app = create_webhook_app(db_path)
    app.run(host=host, port=port, debug=False)


# Global store instance for tool access
_global_store: Optional[MessageStore] = None


def get_message_store() -> MessageStore:
    """Get or create global message store instance."""
    global _global_store
    if _global_store is None:
        from core.config import get_config

        repo_root = get_config().repo_root
        db_path = Path(repo_root) / "auth" / "whatsapp_messages.sqlite"
        _global_store = MessageStore(db_path)
    return _global_store
