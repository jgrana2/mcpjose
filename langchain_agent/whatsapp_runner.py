"""WhatsApp-only interface for the MCP Jose LangChain agent."""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
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
class WhatsAppMediaFetcher:
    access_token: str
    api_version: str = "v22.0"

    def fetch_media(self, media_id: str, output_dir: Optional[Path] = None) -> Path:
        from core.http_client import HTTPClient

        http = HTTPClient()
        http.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        meta = http.get(
            f"https://graph.facebook.com/{self.api_version}/{media_id}"
        ).json()
        url = meta.get("url")
        if not url:
            raise RuntimeError("WhatsApp media URL not found")
        resp = http.get(url)
        out_dir = output_dir or Path(tempfile.gettempdir())
        out_dir.mkdir(parents=True, exist_ok=True)
        mime_type = meta.get("mime_type", "application/octet-stream")
        extension = {
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "video/mp4": ".mp4",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf",
        }.get(mime_type, "")
        safe_mime = mime_type.replace("/", "_")
        path = out_dir / f"whatsapp_{media_id}_{safe_mime}{extension}"
        path.write_bytes(resp.content)
        return path

    def fetch_image(self, media_id: str, output_dir: Optional[Path] = None) -> Path:
        path = self.fetch_media(media_id, output_dir=output_dir)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise RuntimeError(
                f"Unsupported image format for vision: {path.suffix or path.name}"
            )
        return path


@dataclass
class WhatsAppAgentLoop:
    """Poll inbound WhatsApp messages and answer them with the LangChain agent."""

    agent: MCPJoseLangChainAgent
    store: Any
    reply_sender: Callable[[str, str], Dict[str, Any]]
    media_fetcher: Optional[WhatsAppMediaFetcher] = None
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

            sender = _normalize_number(message.from_number)
            if self.allowed_sender and sender != self.allowed_sender:
                continue

            prompt = self._build_prompt(message)
            if not prompt:
                continue

            history = self.history_by_sender.get(sender, [])

            try:
                output = self.agent.run(prompt, chat_history=history).strip()
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

            self._append_turn(sender, prompt, output)
            handled += 1

        return handled

    def _build_prompt(self, message: Any) -> str:
        body = (getattr(message, "body", "") or "").strip()
        caption = (getattr(message, "caption", "") or "").strip()
        msg_type = getattr(message, "type", "")
        media_id = getattr(message, "media_id", None)
        sender = _normalize_number(message.from_number)

        base_prompt = body or caption

        if msg_type == "image" and media_id:
            analysis = self._analyze_image(media_id=media_id, caption=caption)
            if analysis:
                base_prompt = analysis
            else:
                base_prompt = caption or "Analyze this image."
        elif msg_type in {"audio", "voice"} and media_id:
            transcript = self._transcribe_audio(media_id=media_id)
            if transcript:
                base_prompt = transcript
            else:
                base_prompt = caption or "Transcribe this audio message."

        return f"<system>The user's verified phone number is: +{sender}</system>\n{base_prompt}"

    def _transcribe_audio(self, media_id: str) -> str:
        if not self.media_fetcher:
            return ""

        try:
            audio_path = self.media_fetcher.fetch_media(media_id)
        except Exception as exc:
            logger.error("Failed to fetch WhatsApp audio %s: %s", media_id, exc)
            return ""

        try:
            result = self.agent.tool_registry.call_tool(
                "transcribe_audio",
                {"audio_path": str(audio_path)},
            )
        except Exception as exc:
            logger.error("Failed to transcribe WhatsApp audio %s: %s", media_id, exc)
            return ""

        if isinstance(result, dict):
            error = result.get("error")
            if error:
                logger.error("WhatsApp audio transcription returned error: %s", error)
                return ""
            text = (
                result.get("text") or result.get("transcript") or result.get("output")
            )
            if isinstance(text, str) and text.strip():
                return f"Audio transcription for WhatsApp media {media_id}:\n{text.strip()}"
        text = str(result).strip()
        if text:
            return f"Audio transcription for WhatsApp media {media_id}:\n{text}"
        return ""

    def _analyze_image(self, media_id: str, caption: str = "") -> str:
        if not self.media_fetcher:
            return ""

        try:
            image_path = self.media_fetcher.fetch_image(media_id)
        except Exception as exc:
            logger.error("Failed to fetch WhatsApp image %s: %s", media_id, exc)
            return ""

        prompt = (
            "Analyze this WhatsApp image and explain what is visible. "
            "If there is text, extract it. If there are notable objects, people, or scenes, describe them. "
            "Keep the response concise but useful."
        )

        result = self._run_vision_pipeline(image_path=image_path, prompt=prompt)
        if not result:
            return ""

        header = f"Image analysis result for WhatsApp media {media_id}:\n{result}"
        if caption:
            return f"{header}\n\nSender caption: {caption}"
        return header

    def _run_vision_pipeline(self, image_path: Path, prompt: str) -> str:
        vision_prompts = [
            "Use OpenAI vision to analyze the image at {path}. {prompt}",
            "Use Gemini vision to analyze the image at {path}. {prompt}",
        ]
        for template in vision_prompts:
            result = self._call_vision_prompt(template, image_path, prompt)
            if result:
                return result
        return ""

    def _call_vision_prompt(self, template: str, image_path: Path, prompt: str) -> str:
        try:
            result = self.agent.invoke(
                template.format(path=image_path, prompt=prompt),
                chat_history=[],
            )
        except Exception as exc:
            logger.error("Vision analysis failed for %s: %s", image_path, exc)
            return ""

        if isinstance(result, dict):
            output = result.get("output")
            if isinstance(output, str) and output.strip():
                return output.strip()
        return str(result).strip()

    def run_forever(self) -> None:
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


def build_media_fetcher() -> Optional[WhatsAppMediaFetcher]:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    if not token:
        return None
    return WhatsAppMediaFetcher(
        access_token=token,
        api_version=os.getenv("WHATSAPP_API_VERSION", "v22.0"),
    )


def build_media_fetcher_for_message(media_id: str) -> Optional[WhatsAppMediaFetcher]:
    return build_media_fetcher()


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
        media_fetcher=build_media_fetcher(),
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
