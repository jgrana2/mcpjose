from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.tool_registry import ProjectToolRegistry


def test_x_search_runs_without_active_loop(monkeypatch) -> None:
    registry = ProjectToolRegistry()

    async def fake_x_search(topic: str):
        return {"topic": topic, "count": 1, "text": "ok"}

    monkeypatch.setattr(registry, "_x_search_async", fake_x_search)

    result = registry.x_search("AI programming")

    assert result == {"topic": "AI programming", "count": 1, "text": "ok"}


def test_x_search_runs_inside_active_loop(monkeypatch) -> None:
    registry = ProjectToolRegistry()

    async def fake_x_search(topic: str):
        await asyncio.sleep(0)
        return {"topic": topic, "count": 2, "text": "ok from loop"}

    monkeypatch.setattr(registry, "_x_search_async", fake_x_search)

    async def runner():
        return registry.x_search("AI programming")

    result = asyncio.run(runner())

    assert result == {"topic": "AI programming", "count": 2, "text": "ok from loop"}