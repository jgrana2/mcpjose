"""WhatsApp-only interface for the MCP Jose LangChain agent."""

from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from .agent import MCPJoseLangChainAgent

try:
    from langchain_core.messages import AIMessage, HumanMessage
except Exception:  # pragma: no cover - dependency guard
    AIMessage = None
    HumanMessage = None


logger = logging.getLogger(__name__)


def _load_env(repo_root: Path) -> None:
    env_file = repo_root / "auth" / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)


def _normalize_number(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("+"):
        stripped = stripped[1:]
    return "".join(ch for ch in stripped if ch.isdigit())


@dataclass
class WhatsAppReplySender:
    """Send assistant replies over WhatsApp."""

    access_token: str
    phone_number_id: str
    api_version: str = "v22.0"

    def send(self, destination: str, message: str) -> Dict[str, Any]:
        from tools.whatsapp import WhatsAppCloudAPIClient

        client = WhatsAppCloudAPIClient(
            access_token=self.access_token,
            phone_number_id=self.phone_number_id,
            api_version=self.api_version,
        )
        return client.send_text_message(destination=destination, message=message)


@dataclass
class WhatsAppAgentLoop:
    """Poll inbound WhatsApp messages and answer them with the LangChain agent."""

    agent: MCPJoseLangChainAgent
    store: Any
    reply_sender: Callable[[str, str], Dict[str, Any]]
    allowed_sender: Optional[str] = None
    poll_seconds: int = 3
    history_turn_limit: int = 12
    scan_limit: int = 200
    seen_ids: set[str] = field(default_factory=set)
    history_by_sender: Dict[str, List[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.allowed_sender:
            self.allowed_sender = _normalize_number(self.allowed_sender)
        if not self.seen_ids:
            self.seen_ids = {
                message.id for message in self.store.get_recent(limit=self.scan_limit)
            }

    def poll_once(self) -> int:
        """Process any new messages and return the count handled."""
        messages = self.store.get_recent(limit=self.scan_limit)
        fresh = [message for message in messages if message.id not in self.seen_ids]
        fresh.sort(
            key=lambda message: (
                getattr(message, "received_at", "") or "",
                getattr(message, "timestamp", "") or "",
                getattr(message, "id", "") or "",
            )
        )

        handled = 0
        for message in fresh:
            self.seen_ids.add(message.id)

            body = (message.body or "").strip()
            if not body:
                continue

            sender = _normalize_number(message.from_number)
            if self.allowed_sender and sender != self.allowed_sender:
                continue

            history = self.history_by_sender.get(sender, [])

            try:
                output = self.agent.run(body, chat_history=history).strip()
            except Exception as exc:
                output = f"Agent error: {exc}"

            if not output:
                output = "(no response)"

            try:
                self.reply_sender(message.from_number, output)
            except Exception as exc:
                logger.error(
                    "Failed to send WhatsApp reply to %s: %s",
                    sender,
                    exc,
                )
                continue

            self._append_turn(sender, body, output)
            handled += 1

        return handled

    def run_forever(self) -> None:
        """Keep polling until interrupted."""
        while True:
            self.poll_once()
            time.sleep(self.poll_seconds)

    def _append_turn(self, sender: str, prompt: str, response: str) -> None:
        if HumanMessage is None or AIMessage is None:
            return

        history = self.history_by_sender.get(sender, [])
        history = history + [HumanMessage(content=prompt), AIMessage(content=response)]
        max_messages = self.history_turn_limit * 2
        if len(history) > max_messages:
            history = history[-max_messages:]
        self.history_by_sender[sender] = history


def build_reply_sender() -> WhatsAppReplySender:
    return WhatsAppReplySender(
        access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        api_version=os.getenv("WHATSAPP_API_VERSION", "v22.0"),
    )


def run_whatsapp_loop(
    *,
    model: str = "gpt-5.4-mini",
    temperature: float = 0.0,
    max_iterations: int = 12,
    verbose: bool = False,
    allowed_sender: Optional[str] = None,
    poll_seconds: int = 3,
    repo_root: Optional[Path] = None,
) -> None:
    repo_root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    _load_env(repo_root)

    from tools.whatsapp_webhook import get_message_store

    agent = MCPJoseLangChainAgent(
        repo_root=repo_root,
        model=model,
        temperature=temperature,
        max_iterations=max_iterations,
        verbose=verbose,
    )
    store = get_message_store()
    reply_sender = build_reply_sender()
    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=reply_sender.send,
        allowed_sender=allowed_sender or os.getenv("WHATSAPP_DEFAULT_DESTINATION"),
        poll_seconds=poll_seconds,
    )
    loop.run_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the WhatsApp-only agent loop")
    parser.add_argument("--model", default="gpt-5.4-mini", help="OpenAI model")
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Model temperature"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=12, help="Agent iteration cap"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable agent logs")
    parser.add_argument(
        "--allowed-sender",
        default=None,
        help="Only process messages from this WhatsApp number.",
    )
    parser.add_argument(
        "--poll-seconds", type=int, default=3, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    try:
        run_whatsapp_loop(
            model=args.model,
            temperature=args.temperature,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
            allowed_sender=args.allowed_sender,
            poll_seconds=args.poll_seconds,
        )
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
