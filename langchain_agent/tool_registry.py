"""Shared tool registry for MCP Jose surfaces."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from core.config import get_config
from core.http_client import HTTPClient
from core.rate_limit import DailyRateLimiter
from core.utils import is_pdf_file
from providers import ProviderFactory
from providers.search import SearchFactory
from tools.code_editor import (
    _cmd_create,
    _cmd_insert,
    _cmd_str_replace,
    _cmd_undo,
    _cmd_view,
)
from tools.bash_executor import BashExecutor
from tools.filesystem import FilesystemTools
from tools.navigation import extract_html_content, extract_pdf_content
from tools.whatsapp import WhatsAppCloudAPIClient, WhatsAppSendResult
from tools.wolfram_alpha import WolframAlphaClient

from .context import ProjectContextLoader, SkillDocument

try:
    from langchain_core.tools import BaseTool, StructuredTool
except ImportError:  # pragma: no cover - dependency guard
    BaseTool = Any  # type: ignore[assignment]
    StructuredTool = None


def _normalize_e164ish(number: str) -> str:
    stripped = number.strip()
    if stripped.startswith("+"):
        stripped = stripped[1:]
    return "".join(ch for ch in stripped if ch.isdigit())


def _run_async_from_sync(factory: "callable[[], Any]") -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result["value"] = loop.run_until_complete(factory())
        except BaseException as exc:  # pragma: no cover - propagated below
            error["exc"] = exc
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if error:
        raise error["exc"]

    return result["value"]


class ProjectToolRegistry:
    """Wraps project tool functions and exposes them as LangChain tools."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        context_loader: Optional[ProjectContextLoader] = None,
    ) -> None:
        self.repo_root = (repo_root or get_config().repo_root or Path.cwd()).resolve()
        self.context_loader = context_loader or ProjectContextLoader(self.repo_root)
        self.http_client = HTTPClient()
        self.fs_tools = FilesystemTools()

        self._skills_cache: Optional[Dict[str, SkillDocument]] = None
        self._ws_limiter: Optional[DailyRateLimiter] = None
        self._undo_stack: Dict[str, list[str]] = {}

        # Lazy-loaded premium access helpers
        self._guard = None
        self._payment_gateway = None

    def _get_guard(self):
        if self._guard is None:
            from core.guard import SubscriptionGuard
            self._guard = SubscriptionGuard()
        return self._guard

    def _get_payment_gateway(self):
        if self._payment_gateway is None:
            from tools.payment_gateway import PaymentGatewayTool
            self._payment_gateway = PaymentGatewayTool()
        return self._payment_gateway

    def _check_premium_access(self, phone_number: Optional[str]) -> Optional[Dict[str, str]]:
        """Return an error dict if the user lacks an active subscription, else None.

        Generates a checkout link and embeds it in the denial message so users
        know exactly where to subscribe.
        """
        target = phone_number or os.getenv("WHATSAPP_DEFAULT_DESTINATION", "")
        if not target:
            return None  # No phone context — allow (non-WhatsApp callers)

        normalized = f"+{_normalize_e164ish(target)}"
        checkout_url = None
        try:
            result = self._get_payment_gateway().create_checkout_link(normalized)
            checkout_url = result.get("init_point")
        except Exception:
            pass

        error_msg = self._get_guard().check_access(normalized, checkout_url=checkout_url)
        if error_msg:
            return {"error": error_msg}
        return None

    def mp_create_checkout_link(
        self,
        phone_number: str,
        payer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a MercadoPago checkout link for the provided phone number."""
        normalized = f"+{_normalize_e164ish(phone_number)}"
        return self._get_payment_gateway().create_checkout_link(
            normalized,
            payer_email=payer_email,
        )

    def mp_cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a MercadoPago subscription by preapproval id."""
        return self._get_payment_gateway().cancel_subscription(subscription_id)

    # Context / Skills tools
    def read_agents_md(self, max_chars: int = 16000) -> Dict[str, Any]:
        """Read AGENTS.md project guidance."""
        content = self.context_loader.load_agents_guidance()
        truncated = len(content) > max_chars
        return {
            "path": str(self.context_loader.agents_path()),
            "content": content[:max_chars],
            "truncated": truncated,
            "total_chars": len(content),
        }

    def list_skills(self) -> Dict[str, Any]:
        """List all discovered SKILL.md entries in this repository."""
        skills = self._load_skills()
        items = [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
            }
            for skill in skills.values()
        ]
        return {"skills": items, "count": len(items)}

    def read_skill(self, skill_name: str, max_chars: int = 16000) -> Dict[str, Any]:
        """Read one skill by id or folder name."""
        skill = self._find_skill(skill_name)
        if not skill:
            return {
                "error": f"Skill '{skill_name}' was not found.",
                "hint": "Call list_skills to get valid skill ids.",
            }

        content = skill.content
        truncated = len(content) > max_chars
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "path": str(skill.path),
            "description": skill.description,
            "content": content[:max_chars],
            "truncated": truncated,
            "total_chars": len(content),
        }

    # Memory tools
    def save_memory(
        self, summary: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Save interaction to long-term memory."""
        from core.memory import MemoryService

        MemoryService().save_interaction(summary, content, metadata if metadata else {})
        return {"status": "success"}

    def query_memory(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query long-term memory using semantic search."""
        from core.memory import MemoryService

        return MemoryService().query_memory(query, n_results)

    def search(self, query: str) -> Dict[str, Any]:
        """Search the web using configured provider (DuckDuckGo or Google PSE)."""
        return SearchFactory.create().search(query)

    def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Fetch and extract content from URL (HTML/PDF)."""
        try:
            if is_pdf_file(url):
                pdf_content = extract_pdf_content(url, self.http_client)
                if pdf_content:
                    return {"content": pdf_content, "url": url, "type": "pdf"}

            content = extract_html_content(url, self.http_client)
            return {"content": content, "url": url, "type": "html"}
        except Exception as exc:
            return {"error": f"Error navigating to {url}: {exc}", "url": url}

    def x_search(self, topic: str) -> Dict[str, Any]:
        """Search recent X/Twitter posts using twscrape."""
        try:
            return _run_async_from_sync(lambda: self._x_search_async(topic))
        except Exception as exc:
            return {"error": f"x_search failed: {exc}", "topic": topic}

    async def _x_search_async(self, topic: str) -> Dict[str, Any]:
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "about",
            "how",
            "what",
            "when",
            "where",
            "who",
            "why",
            "which",
            "de",
            "para",
            "con",
            "sin",
            "la",
            "el",
            "los",
            "las",
            "un",
            "una",
            "unos",
            "unas",
        }

        words = topic.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        search_query = " ".join((keywords or words)[:3])

        try:
            from twscrape import API
        except Exception as exc:
            return {"error": f"twscrape is unavailable: {exc}", "topic": topic}

        api = API()
        username = os.getenv("TWSCRAPE_USERNAME")
        password = os.getenv("TWSCRAPE_PASSWORD")
        email = os.getenv("TWSCRAPE_EMAIL_TWO")
        api_key = os.getenv("TWSCRAPE_API_KEY")
        cookies_str = os.getenv("TWSCRAPE_COOKIES")
        if not all([username, password, email, api_key, cookies_str]):
            return {
                "error": "Missing required TwScrape environment variables.",
                "topic": topic,
                "search_query": search_query,
            }

        await api.pool.add_account(
            username, password, email, api_key, cookies=cookies_str
        )

        posts: list[str] = []
        try:
            async for tweet in api.search(search_query, limit=20):
                posts.append(tweet.rawContent)
        except Exception as exc:
            return {
                "error": f"Failed to search tweets: {exc}",
                "topic": topic,
                "search_query": search_query,
            }

        return {
            "text": "\n\n---POST---\n\n".join(posts),
            "count": len(posts),
            "topic": topic,
            "search_query": search_query,
        }

    # AI tools
    def call_llm(self, prompt: str, phone_number: Optional[str] = None) -> Dict[str, str]:
        """Generate text with the OpenAI LLM provider."""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        try:
            provider = ProviderFactory.create_llm("openai")
            return {"text": provider.complete(prompt)}
        except Exception as exc:
            return {"error": f"call_llm failed: {exc}"}

    def openai_vision_tool(
        self,
        image_path: str,
        prompt: str,
        ocr_context: Optional[str] = None,
        ocr_file: Optional[str] = None,
        model: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, str]:
        """Process images/PDF pages with OpenAI vision."""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        if ocr_file:
            ocr_path = Path(ocr_file)
            if not ocr_path.exists():
                return {"error": f"OCR file not found: {ocr_file}"}
            ocr_context = ocr_path.read_text(encoding="utf-8")

        try:
            provider = ProviderFactory.create_vision("openai")
            result = provider.process_image(
                image_path=image_path,
                prompt=prompt,
                ocr_context=ocr_context,
                model=model,
            )
            return {"text": result}
        except Exception as exc:
            return {"error": f"openai_vision_tool failed: {exc}"}

    def gemini_vision_tool(
        self,
        image_path: str,
        prompt: str,
        ocr_context: Optional[str] = None,
        ocr_file: Optional[str] = None,
        model: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, str]:
        """Process images/PDF pages with Gemini vision."""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        if ocr_file:
            ocr_path = Path(ocr_file)
            if not ocr_path.exists():
                return {"error": f"OCR file not found: {ocr_file}"}
            ocr_context = ocr_path.read_text(encoding="utf-8")

        try:
            provider = ProviderFactory.create_vision("gemini")
            result = provider.process_image(
                image_path=image_path,
                prompt=prompt,
                ocr_context=ocr_context,
                model=model,
            )
            return {"text": result}
        except Exception as exc:
            return {"error": f"gemini_vision_tool failed: {exc}"}

    def generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate or edit an image with Gemini. (Premium Tool)"""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        try:
            provider = ProviderFactory.create_image_generator("gemini")
            return provider.generate(prompt, output_path, image_path)
        except Exception as exc:
            return {"error": f"generate_image failed: {exc}"}

    def google_ocr(
        self,
        input_file: str,
        file_type: Optional[str] = None,
        output: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract OCR text from image or PDF using Google Vision."""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        try:
            provider = ProviderFactory.create_ocr("google")
            annotations = provider.extract_text(input_file, file_type)
            result: Dict[str, Any] = {"annotations": annotations}
            if output:
                provider.save_annotations(annotations, output)
                result["output_path"] = output
            return result
        except Exception as exc:
            return {"error": f"google_ocr failed: {exc}"}

    def transcribe_audio(
        self,
        audio_path: str,
        model: str = "gpt-4o-transcribe",
        language: Optional[str] = None,
        response_format: str = "text",
        timestamp_granularities: Optional[list[str]] = None,
        prompt: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transcribe audio with OpenAI transcription models."""
        access_error = self._check_premium_access(phone_number)
        if access_error:
            return access_error
        try:
            provider = ProviderFactory.create_transcription("openai")
            kwargs: Dict[str, Any] = {
                "model": model,
                "response_format": response_format,
            }
            if language:
                kwargs["language"] = language
            if timestamp_granularities:
                kwargs["timestamp_granularities"] = timestamp_granularities
            if prompt:
                kwargs["prompt"] = prompt

            result = provider.transcribe(audio_path, **kwargs)
            if response_format == "text":
                if isinstance(result, str):
                    return {"text": result}
                return {"text": getattr(result, "text", str(result))}

            if hasattr(result, "model_dump"):
                return result.model_dump()
            if hasattr(result, "dict"):
                return result.dict()
            return {"result": str(result)}
        except Exception as exc:
            return {"error": f"transcribe_audio failed: {exc}"}

    def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        place_type: Optional[str] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Search for places using Google Maps Places API."""
        try:
            provider = ProviderFactory.create_maps("google")
            results = provider.search_places(
                query=query,
                location=location,
                radius=radius,
                place_type=place_type,
                max_results=max_results,
            )
            return {
                "success": True,
                "query": query,
                "count": len(results),
                "results": results,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "query": query}

    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a place using Google Maps."""
        try:
            provider = ProviderFactory.create_maps("google")
            details = provider.get_place_details(place_id)
            return {
                "success": True,
                "place_id": place_id,
                "details": details,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "place_id": place_id}

    def wolfram_alpha(
        self,
        query: str,
        maxchars: Optional[int] = None,
        units: Optional[str] = None,
        assumption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query Wolfram Alpha's LLM API for factual or computed answers."""
        try:
            client = WolframAlphaClient(
                app_id=os.getenv("WOLFRAM_ALPHA_APP_ID", ""),
                http_client=self.http_client,
            )
            return client.query(
                query=query,
                maxchars=maxchars,
                units=units,
                assumption=assumption,
            )
        except Exception as exc:
            return {
                "ok": False,
                "provider": "wolfram_alpha",
                "query": query,
                "error": str(exc),
            }

    # WhatsApp tool
    def send_ws_msg(
        self,
        destination: Optional[str] = None,
        message: str = "",
        template_name: Optional[str] = None,
        language_code: Optional[str] = None,
        image_path: Optional[str] = None,
        media_path: Optional[str] = None,
        media_url: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send WhatsApp message or image using Meta Cloud API with local daily limit.

        For text messages, provide `destination` and `message`.
        For image messages, additionally provide one of:
          - `image_path` / `media_path`: local file path — the file is uploaded to
            WhatsApp Cloud API and sent as an image; `message` becomes the caption.
          - `media_url`: a public URL to an image — sent directly without uploading.
        Do not provide both a local path and `media_url` at the same time.
        """
        default_destination = os.getenv("WHATSAPP_DEFAULT_DESTINATION")
        dest = destination or (default_destination or "").strip()
        if not dest:
            return WhatsAppSendResult(
                ok=False,
                destination="",
                provider="whatsapp_cloud_api",
                error="Missing destination. Provide one or set WHATSAPP_DEFAULT_DESTINATION.",
            ).to_dict()

        normalized = _normalize_e164ish(dest)
        if not message.strip():
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error="Message must be a non-empty string.",
            ).to_dict()

        daily_max = int(os.getenv("WHATSAPP_DAILY_MAX", "10"))
        rate = self._get_ws_limiter().consume(
            scope="send_ws_msg",
            limit=daily_max,
            amount=1,
            tz=self._whatsapp_timezone(),
        )
        if not rate.allowed:
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error=f"Daily rate limit exceeded for send_ws_msg ({daily_max}/day).",
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()

        try:
            client = WhatsAppCloudAPIClient(
                access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
                phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
                api_version=os.getenv("WHATSAPP_API_VERSION", "v22.0"),
            )

            effective_template = template_name or os.getenv("WHATSAPP_TEMPLATE_NAME")
            effective_lang = language_code or os.getenv(
                "WHATSAPP_TEMPLATE_LANGUAGE", "en_US"
            )
            media_source = image_path or media_path

            if media_source:
                if media_url:
                    return WhatsAppSendResult(
                        ok=False,
                        destination=normalized,
                        provider=client.name,
                        error="Provide either a local media path or media_url, not both.",
                        rate_limit_day=rate.day,
                        rate_limit_used=rate.used,
                        rate_limit_limit=rate.limit,
                        rate_limit_remaining=rate.remaining,
                    ).to_dict()
                media_id = client.upload_media(media_source, mime_type=mime_type)
                result = client.send_image_message(
                    normalized, media_id=media_id, caption=message.strip()
                )
            elif media_url:
                # For media_url, construct the payload manually since send_image_message
                # only accepts media_id
                payload = {
                    "messaging_product": "whatsapp",
                    "to": _normalize_e164ish(normalized),
                    "type": "image",
                    "image": {"link": media_url, "caption": message.strip()},
                }
                url = f"https://graph.facebook.com/{client.api_version}/{client.phone_number_id}/messages"
                result = client.http.post(url, json=payload).json()
            else:
                result = client.send_text_message(
                    destination=normalized,
                    message=message.strip(),
                    template_name=effective_template,
                    language_code=effective_lang,
                )

            message_id = None
            if isinstance(result, dict):
                messages = result.get("messages")
                if isinstance(messages, list) and messages:
                    message_id = messages[0].get("id")

            return WhatsAppSendResult(
                ok=True,
                destination=normalized,
                provider=client.name,
                message_id=message_id,
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()
        except Exception as exc:
            return WhatsAppSendResult(
                ok=False,
                destination=normalized,
                provider="whatsapp_cloud_api",
                error=str(exc),
                rate_limit_day=rate.day,
                rate_limit_used=rate.used,
                rate_limit_limit=rate.limit,
                rate_limit_remaining=rate.remaining,
            ).to_dict()

    def get_ws_messages(
        self,
        limit: int = 10,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve recent WhatsApp webhook messages from local storage."""
        try:
            from tools.webhook_server import get_message_store

            store = get_message_store()
            messages = store.get_recent(limit=limit, since=since)
            return {
                "ok": True,
                "messages": [message.to_dict() for message in messages],
                "count": len(messages),
            }
        except Exception as exc:
            return {"ok": False, "messages": [], "count": 0, "error": str(exc)}

    # Filesystem tools
    def read_file(
        self,
        path: str,
        head: Optional[int] = None,
        tail: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Read file content with optional head/tail lines."""
        return self.fs_tools.read_text_file(path, head=head, tail=tail)

    def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory entries."""
        return self.fs_tools.list_directory(path)

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write text content to file."""
        return self.fs_tools.write_file(path, content)

    def create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory recursively."""
        return self.fs_tools.create_directory(path)

    def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """Move or rename a file."""
        return self.fs_tools.move_file(source, destination)

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file or directory metadata."""
        return self.fs_tools.get_file_info(path)

    def search_files(
        self,
        path: str,
        pattern: str,
        exclude_patterns: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Find files under a path using glob pattern matching."""
        return self.fs_tools.search_files(path, pattern, exclude_patterns)

    def list_allowed_directories(self) -> Dict[str, Any]:
        """List paths allowed by filesystem tools."""
        return self.fs_tools.list_allowed_directories()

    def str_replace_editor(
        self,
        command: str,
        path: str,
        file_text: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        insert_line: Optional[int] = None,
        view_range: Optional[list[int]] = None,
    ) -> Dict[str, Any]:
        """View, create, and edit files using the str_replace_editor pattern.

        Commands: view, create, str_replace, insert, undo_edit.
        """
        try:
            resolved = self.fs_tools._validate_path(path)
        except ValueError as e:
            return {"error": str(e)}

        if command == "view":
            return _cmd_view(resolved, view_range)
        if command == "create":
            return _cmd_create(resolved, file_text, self._undo_stack)
        if command == "str_replace":
            return _cmd_str_replace(resolved, old_str, new_str, self._undo_stack)
        if command == "insert":
            return _cmd_insert(resolved, insert_line, new_str, self._undo_stack)
        if command == "undo_edit":
            return _cmd_undo(resolved, self._undo_stack)
        return {
            "error": f"Unknown command '{command}'. Use: view, create, str_replace, insert, undo_edit."
        }

    def bash_execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute a bash command and return stdout, stderr, and return code."""
        try:
            return BashExecutor().execute(command, cwd=cwd, timeout=timeout)
        except Exception as exc:
            return {"ok": False, "error": f"bash_execute failed: {exc}"}

    def tool_specs(self) -> list[tuple[str, str, Any]]:
        """Return the canonical shared tool definitions."""
        return [
            (
                "mp_create_checkout_link",
                "Generate a MercadoPago Checkout Pro subscription link for a phone number.",
                self.mp_create_checkout_link,
            ),
            (
                "mp_cancel_subscription",
                "Cancel a MercadoPago subscription by preapproval id.",
                self.mp_cancel_subscription,
            ),
            ("search", "Search the web using configured search backend.", self.search),
            (
                "navigate_to_url",
                "Read URL content, including HTML pages and PDFs.",
                self.navigate_to_url,
            ),
            (
                "x_search",
                "Search X/Twitter posts using deterministic keyword matching.",
                self.x_search,
            ),
            ("call_llm", "Generate text using OpenAI LLM provider.", self.call_llm),
            (
                "openai_vision_tool",
                "Analyze an image/PDF page using OpenAI vision.",
                self.openai_vision_tool,
            ),
            (
                "gemini_vision_tool",
                "Analyze an image/PDF page using Gemini vision.",
                self.gemini_vision_tool,
            ),
            (
                "generate_image",
                "Generate or edit images with Gemini image generation.",
                self.generate_image,
            ),
            ("google_ocr", "Extract OCR text from image/PDF.", self.google_ocr),
            (
                "transcribe_audio",
                "Transcribe speech from audio file with OpenAI.",
                self.transcribe_audio,
            ),
            (
                "search_places",
                "Search for places with Google Maps Places API.",
                self.search_places,
            ),
            (
                "get_place_details",
                "Get place details from Google Maps Places API.",
                self.get_place_details,
            ),
            (
                "wolfram_alpha",
                "Query Wolfram Alpha for exact or computed answers.",
                self.wolfram_alpha,
            ),
            (
                "send_ws_msg",
                "Send WhatsApp message through Meta Cloud API.",
                self.send_ws_msg,
            ),
            (
                "get_ws_messages",
                "Read recent WhatsApp webhook messages from local storage.",
                self.get_ws_messages,
            ),
            (
                "read_file",
                "Read a local text file with optional head/tail slicing.",
                self.read_file,
            ),
            ("list_directory", "List local directory contents.", self.list_directory),
            ("write_file", "Write text to a local file.", self.write_file),
            (
                "create_directory",
                "Create a local directory recursively.",
                self.create_directory,
            ),
            ("move_file", "Move or rename a local file/directory.", self.move_file),
            (
                "get_file_info",
                "Get metadata for local file/directory.",
                self.get_file_info,
            ),
            (
                "search_files",
                "Search local files recursively by glob pattern.",
                self.search_files,
            ),
            (
                "list_allowed_directories",
                "List directories allowed for filesystem access.",
                self.list_allowed_directories,
            ),
            (
                "str_replace_editor",
                "View, create, and edit local files (commands: view, create, str_replace, insert, undo_edit).",
                self.str_replace_editor,
            ),
            (
                "bash_execute",
                "Run a bash command and capture stdout, stderr, and return code.",
                self.bash_execute,
            ),
            ("read_agents_md", "Read AGENTS.md instructions.", self.read_agents_md),
            ("list_skills", "List all discovered project skills.", self.list_skills),
            ("read_skill", "Read a skill by name or skill_id.", self.read_skill),
            ("save_memory", "Save interaction to long-term memory.", self.save_memory),
            (
                "query_memory",
                "Query long-term memory using semantic search.",
                self.query_memory,
            ),
        ]

    def list_tool_specs(self) -> list[dict[str, str]]:
        """Return shared tool metadata for CLI/UI consumers."""
        return [
            {"name": name, "description": description}
            for name, description, _func in self.tool_specs()
        ]

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call a shared tool by name with keyword arguments."""
        tools = {tool_name: func for tool_name, _description, func in self.tool_specs()}
        if name not in tools:
            available = ", ".join(sorted(tools))
            raise ValueError(f"Unknown tool '{name}'. Available tools: {available}")

        return tools[name](**(arguments or {}))

    def register_mcp_tools(self, mcp: Any) -> None:
        """Register the canonical shared tools with an MCP server."""
        for _name, _description, func in self.tool_specs():
            mcp.tool()(func)

    def as_langchain_tools(self) -> list[BaseTool]:
        """Build LangChain StructuredTool objects for all project tools."""
        if StructuredTool is None:
            raise RuntimeError(
                "langchain-core is not installed. Install langchain + langchain-openai."
            )

        return [
            StructuredTool.from_function(
                func=func,
                name=name,
                description=description,
            )
            for name, description, func in self.tool_specs()
        ]

    def _load_skills(self) -> Dict[str, SkillDocument]:
        if self._skills_cache is None:
            self._skills_cache = self.context_loader.load_skills()
        return self._skills_cache

    def _find_skill(self, skill_name: str) -> Optional[SkillDocument]:
        skills = self._load_skills()
        if skill_name in skills:
            return skills[skill_name]

        for skill in skills.values():
            if skill.name == skill_name:
                return skill
        return None

    def _get_ws_limiter(self) -> DailyRateLimiter:
        if self._ws_limiter is None:
            rate_path = self.repo_root / "auth" / "rate_limits.sqlite"
            self._ws_limiter = DailyRateLimiter.from_env(default_path=rate_path)
        return self._ws_limiter

    @staticmethod
    def _whatsapp_timezone():
        tz_name = os.getenv("WHATSAPP_TIMEZONE")
        if tz_name:
            return ZoneInfo(tz_name)
        return datetime.now().astimezone().tzinfo
