"""Tests for the WhatsApp-only LangChain agent loop."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_agent.whatsapp_runner import WhatsAppAgentLoop


@dataclass
class _Message:
    id: str
    from_number: str
    body: str = ""
    received_at: str = ""
    timestamp: str = ""
    type: str = "text"
    caption: str = ""
    media_id: str | None = None


class _Store:
    def __init__(self, messages: list[_Message]):
        self.messages = messages

    def get_recent(self, limit: int = 200) -> list[_Message]:
        return list(self.messages)[-limit:]


class _Agent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []
        self.tool_registry = self

    def run(self, user_input: str, chat_history=None) -> str:
        history = list(chat_history or [])
        self.calls.append((user_input, history))
        return f"reply: {user_input}"

    def invoke(self, user_input: str, chat_history=None):
        return {"output": f"vision: {user_input}"}

    def call_tool(self, name: str, args: dict[str, object]):
        if name == "transcribe_audio":
            return {"text": f"transcript for {args['audio_path']}"}
        return {"output": ""}


class _Sender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, destination: str, message: str) -> dict[str, object]:
        self.sent.append((destination, message))
        return {"ok": True}


class _FailingSender:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send(self, destination: str, message: str) -> dict[str, object]:
        self.calls.append((destination, message))
        raise RuntimeError("token expired")


class _Fetcher:
    def __init__(self, path: str = "/tmp/example.jpg") -> None:
        self.calls: list[str] = []
        self.path = path

    def fetch_image(self, media_id: str):
        self.calls.append(media_id)
        return self.path

    def fetch_media(self, media_id: str):
        self.calls.append(media_id)
        return self.path


def test_poll_once_routes_new_messages_through_agent_and_reply_sender() -> None:
    store = _Store([_Message("seed", "573002612420", "seed", "2026-03-19T19:00:00")])
    agent = _Agent()
    sender = _Sender()

    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=sender.send,
        allowed_sender="573002612420",
        scan_limit=10,
    )

    store.messages.extend(
        [
            _Message("m1", "573002612420", "First prompt", "2026-03-19T19:01:00"),
            _Message("m2", "573002612420", "Second prompt", "2026-03-19T19:02:00"),
        ]
    )

    handled = loop.poll_once()

    assert handled == 2
    assert [call[0].split("\n", 1)[1] for call in agent.calls] == ["First prompt", "Second prompt"]
    assert len(agent.calls[0][1]) == 0
    assert len(agent.calls[1][1]) == 2
    assert sender.sent == [("573002612420", "reply: " + agent.calls[0][0]), ("573002612420", "reply: " + agent.calls[1][0])]


def test_poll_once_allows_multiple_senders() -> None:
    store = _Store(
        [
            _Message("seed", "573002612420", "seed", "2026-03-19T19:00:00"),
            _Message("seed2", "573166275240", "seed", "2026-03-19T19:00:00"),
        ]
    )
    agent = _Agent()
    sender = _Sender()

    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=sender.send,
        allowed_senders={"573002612420", "573166275240"},
        scan_limit=10,
    )

    store.messages.extend(
        [
            _Message("m1", "573002612420", "First prompt", "2026-03-19T19:01:00"),
            _Message("m2", "573166275240", "Second prompt", "2026-03-19T19:02:00"),
        ]
    )

    handled = loop.poll_once()

    assert handled == 2
    assert [call[0].split("\n", 1)[1] for call in agent.calls] == ["First prompt", "Second prompt"]
    assert sender.sent == [("573002612420", "reply: " + agent.calls[0][0]), ("573166275240", "reply: " + agent.calls[1][0])]


def test_poll_once_continues_when_reply_sender_fails(caplog) -> None:
    store = _Store([_Message("seed", "573002612420", "seed", "2026-03-19T19:00:00")])
    agent = _Agent()
    sender = _FailingSender()

    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=sender.send,
        allowed_sender="573002612420",
        scan_limit=10,
    )

    store.messages.extend(
        [
            _Message("m1", "573002612420", "First prompt", "2026-03-19T19:01:00"),
            _Message("m2", "573002612420", "Second prompt", "2026-03-19T19:02:00"),
        ]
    )

    handled = loop.poll_once()

    assert handled == 0
    assert [call[0].split("\n", 1)[1] for call in agent.calls] == ["First prompt", "Second prompt"]
    assert sender.calls == [("573002612420", "reply: " + agent.calls[0][0]), ("573002612420", "reply: " + agent.calls[1][0])]
    assert "Failed to send WhatsApp reply" in caplog.text


def test_poll_once_auto_analyzes_image_messages_with_fetcher() -> None:
    store = _Store([_Message("seed", "573002612420", "seed", "2026-03-19T19:00:00")])
    agent = _Agent()
    sender = _Sender()
    fetcher = _Fetcher("/tmp/whatsapp_media.jpg")

    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=sender.send,
        media_fetcher=fetcher,
        allowed_sender="573002612420",
        scan_limit=10,
    )

    store.messages.append(
        _Message(
            "img1",
            "573002612420",
            "",
            "2026-03-19T19:03:00",
            type="image",
            caption="Check this out",
            media_id="media-123",
        )
    )

    handled = loop.poll_once()

    assert handled == 1
    assert fetcher.calls == ["media-123"]
    assert "Image analysis result for WhatsApp media media-123" in agent.calls[0][0]
    assert "Sender caption: Check this out" in agent.calls[0][0]
    assert sender.sent == [("573002612420", "reply: " + agent.calls[0][0])]


def test_poll_once_auto_transcribes_audio_messages_with_fetcher() -> None:
    store = _Store([_Message("seed", "573002612420", "seed", "2026-03-19T19:00:00")])
    agent = _Agent()
    sender = _Sender()
    fetcher = _Fetcher("/tmp/whatsapp_audio.m4a")

    loop = WhatsAppAgentLoop(
        agent=agent,
        store=store,
        reply_sender=sender.send,
        media_fetcher=fetcher,
        allowed_sender="573002612420",
        scan_limit=10,
    )

    store.messages.append(
        _Message(
            "audio1",
            "573002612420",
            "",
            "2026-03-19T19:03:00",
            type="audio",
            media_id="media-audio-123",
        )
    )

    handled = loop.poll_once()

    assert handled == 1
    assert fetcher.calls == ["media-audio-123"]
    assert "transcript for /tmp/whatsapp_audio.m4a" in agent.calls[0][0]
    assert sender.sent == [("573002612420", "reply: " + agent.calls[0][0])]
