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


def _parse_allowed_senders(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {
        _normalize_number(part)
        for part in value.split(",")
        if _normalize_number(part)
    }


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

    def fetch_media(
        self,
        media_id: str,
        output_dir: Optional[Path] = None,
        filename: Optional[str] = None,
    ) -> Path:
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

        if filename:
            path = out_dir / f"whatsapp_{media_id}_{filename}"
            path.write_bytes(resp.content)
            return path

        extension = {
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "video/mp4": ".mp4",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "application/msword": ".doc",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.ms-powerpoint": ".ppt",
            "text/plain": ".txt",
            "text/csv": ".csv",
            "application/zip": ".zip",
            "application/json": ".json",
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
    allowed_senders: set[str] = field(default_factory=set)
    poll_seconds: int = 3
    history_turn_limit: int = 12
    scan_limit: int = 200
    seen_ids: set[str] = field(default_factory=set)
    history_by_sender: Dict[str, List[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.allowed_sender:
            self.allowed_senders.add(_normalize_number(self.allowed_sender))
        self.allowed_senders = {
            _normalize_number(sender) for sender in self.allowed_senders if sender
        }
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
            if self.allowed_senders and sender not in self.allowed_senders:
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
            analysis = self._analyze_image(media_id=media_id, caption=caption, sender=sender)
            if analysis:
                base_prompt = analysis
            else:
                base_prompt = caption or "Analyze this image."
        elif msg_type in {"audio", "voice"} and media_id:
            transcript = self._transcribe_audio(media_id=media_id, sender=sender)
            if transcript:
                base_prompt = transcript
            else:
                base_prompt = caption or "Transcribe this audio message."
        elif msg_type == "document" and media_id:
            doc_info = self._process_document(
                media_id=media_id,
                caption=caption,
                sender=sender,
                message=message,
            )
            if doc_info:
                base_prompt = doc_info
            else:
                base_prompt = caption or "A document was sent but could not be processed."
        elif msg_type == "video" and media_id:
            filename = getattr(message, "filename", None)
            base_prompt = self._describe_received_media(
                media_id=media_id,
                media_type="video",
                caption=caption,
                filename=filename,
            )

        return f"<system>The user's verified phone number is: +{sender}</system>\n{base_prompt}"

    def _transcribe_audio(self, media_id: str, sender: str = "") -> str:
        if not self.media_fetcher:
            return ""

        try:
            audio_path = self.media_fetcher.fetch_media(media_id)
        except Exception as exc:
            logger.error("Failed to fetch WhatsApp audio %s: %s", media_id, exc)
            return ""

        try:
            args: Dict[str, Any] = {"audio_path": str(audio_path)}
            if sender:
                args["phone_number"] = f"+{sender}"
            result = self.agent.tool_registry.call_tool("transcribe_audio", args)
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

    def _analyze_image(self, media_id: str, caption: str = "", sender: str = "") -> str:
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

        result = self._run_vision_pipeline(image_path=image_path, prompt=prompt, sender=sender)
        if not result:
            return ""

        header = f"Image analysis result for WhatsApp media {media_id}:\n{result}"
        if caption:
            return f"{header}\n\nSender caption: {caption}"
        return header

    def _run_vision_pipeline(self, image_path: Path, prompt: str, sender: str = "") -> str:
        vision_prompts = [
            "Use OpenAI vision to analyze the image at {path}. {prompt}",
            "Use Gemini vision to analyze the image at {path}. {prompt}",
        ]
        for template in vision_prompts:
            result = self._call_vision_prompt(template, image_path, prompt, sender=sender)
            if result:
                return result
        return ""

    def _call_vision_prompt(self, template: str, image_path: Path, prompt: str, sender: str = "") -> str:
        phone_context = f"<system>The user's verified phone number is: +{sender}</system>\n" if sender else ""
        try:
            result = self.agent.invoke(
                phone_context + template.format(path=image_path, prompt=prompt),
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

    def _process_document(
        self,
        media_id: str,
        caption: str = "",
        sender: str = "",
        message: Any = None,
    ) -> str:
        """Download a document from WhatsApp and build a prompt with its content."""
        if not self.media_fetcher:
            return ""

        filename = getattr(message, "filename", None) if message else None

        try:
            file_path = self.media_fetcher.fetch_media(
                media_id, filename=filename,
            )
        except Exception as exc:
            logger.error("Failed to fetch WhatsApp document %s: %s", media_id, exc)
            return ""

        suffix = file_path.suffix.lower()
        content_summary = ""

        if suffix == ".pdf":
            try:
                content_summary = extract_pdf_content(str(file_path))
                if content_summary:
                    content_summary = content_summary[:8000]
            except Exception as exc:
                logger.warning("PDF extraction failed for %s: %s", file_path, exc)

        elif suffix in {".txt", ".csv", ".json", ".md", ".log", ".xml", ".html"}:
            try:
                content_summary = file_path.read_text(errors="replace")[:8000]
            except Exception as exc:
                logger.warning("Text read failed for %s: %s", file_path, exc)

        parts = [
            f"The user sent a document via WhatsApp (media_id={media_id}).",
            f"File saved locally at: {file_path}",
        ]
        if filename:
            parts.append(f"Original filename: {filename}")
        if content_summary:
            parts.append(f"Extracted content (first 8000 chars):\n{content_summary}")
        else:
            parts.append(
                "The file type could not be read inline. "
                "Use available tools (bash, filesystem, OCR, vision) to inspect it."
            )
        if caption:
            parts.append(f"Sender caption: {caption}")

        return "\n\n".join(parts)

    def _describe_received_media(
        self,
        media_id: str,
        media_type: str,
        caption: str = "",
        filename: Optional[str] = None,
    ) -> str:
        parts = [f"The user sent a {media_type} via WhatsApp (media_id={media_id})."]
        if filename:
            parts.append(f"Original filename: {filename}")
        if self.media_fetcher:
            try:
                file_path = self.media_fetcher.fetch_media(
                    media_id, filename=filename,
                )
                parts.append(f"File saved locally at: {file_path}")
            except Exception as exc:
                logger.error("Failed to fetch WhatsApp %s %s: %s", media_type, media_id, exc)
        if caption:
            parts.append(f"Sender caption: {caption}")
        return "\n\n".join(parts)

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
    allowed_senders: Optional[str] = None,
    poll_seconds: int = 3,
    repo_root: Optional[Path] = None,
) -> None:
    repo_root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    _load_env(repo_root)

    from tools.webhook_server import get_message_store

    agent = MCPJoseLangChainAgent(
        repo_root=repo_root,
        model=model,
        temperature=temperature,
        max_iterations=max_iterations,
        verbose=verbose,
    )
    store = get_message_store()
    reply_sender = build_reply_sender()
    configured_senders = _parse_allowed_senders(
        allowed_senders or os.getenv("WHATSAPP_ALLOWED_SENDERS")
    )
    if allowed_sender:
        configured_senders.add(_normalize_number(allowed_sender))
    fallback_sender = os.getenv("WHATSAPP_DEFAULT_DESTINATION")
    if fallback_sender and not configured_senders:
        configured_senders.add(_normalize_number(fallback_sender))
    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=reply_sender.send,
        media_fetcher=build_media_fetcher(),
        allowed_senders=configured_senders,
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
        "--allowed-senders",
        default=None,
        help="Comma-separated list of WhatsApp numbers allowed to trigger the agent.",
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
            allowed_senders=args.allowed_senders,
            poll_seconds=args.poll_seconds,
        )
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
