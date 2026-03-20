"""Tests for the WhatsApp-only LangChain agent loop."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_agent.whatsapp_runner import WhatsAppAgentLoop


@dataclass
class _Message:
    id: str
    from_number: str
    body: str
    received_at: str
    timestamp: str = ""


class _Store:
    def __init__(self, messages: list[_Message]):
        self.messages = messages

    def get_recent(self, limit: int = 200) -> list[_Message]:
        return list(self.messages)[-limit:]


class _Agent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    def run(self, user_input: str, chat_history=None) -> str:
        history = list(chat_history or [])
        self.calls.append((user_input, history))
        return f"reply: {user_input}"


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


def test_poll_once_routes_new_messages_through_agent_and_reply_sender() -> None:
    store = _Store(
        [
            _Message("seed", "573002612420", "seed", "2026-03-19T19:00:00"),
        ]
    )
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
    assert [call[0] for call in agent.calls] == ["First prompt", "Second prompt"]
    assert len(agent.calls[0][1]) == 0
    assert len(agent.calls[1][1]) == 2
    assert sender.sent == [
        ("573002612420", "reply: First prompt"),
        ("573002612420", "reply: Second prompt"),
    ]


def test_poll_once_continues_when_reply_sender_fails(caplog) -> None:
    store = _Store(
        [
            _Message("seed", "573002612420", "seed", "2026-03-19T19:00:00"),
        ]
    )
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
    assert [call[0] for call in agent.calls] == ["First prompt", "Second prompt"]
    assert sender.calls == [
        ("573002612420", "reply: First prompt"),
        ("573002612420", "reply: Second prompt"),
    ]
    assert "Failed to send WhatsApp reply" in caplog.text
