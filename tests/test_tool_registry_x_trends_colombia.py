from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_agent.tool_registry import ProjectToolRegistry


def test_x_trends_colombia_runs_without_active_loop(monkeypatch) -> None:
    registry = ProjectToolRegistry()

    async def fake_x_trends(limit: int = 20):
        return {
            "country": "Colombia",
            "woeid": 368148,
            "count": 1,
            "trends": [{"rank": 1, "name": "#Topic", "tweet_volume": 1000}],
            "limit": limit,
        }

    monkeypatch.setattr(registry, "_x_trends_colombia_async", fake_x_trends)

    result = registry.x_trends_colombia(limit=10)

    assert result["country"] == "Colombia"
    assert result["woeid"] == 368148
    assert result["count"] == 1
    assert result["limit"] == 10
    assert result["trends"][0]["rank"] == 1


def test_x_trends_colombia_runs_inside_active_loop(monkeypatch) -> None:
    registry = ProjectToolRegistry()

    async def fake_x_trends(limit: int = 20):
        await asyncio.sleep(0)
        return {
            "country": "Colombia",
            "woeid": 368148,
            "count": 2,
            "trends": [{"rank": 1, "name": "#TopicA"}, {"rank": 2, "name": "#TopicB"}],
            "limit": limit,
        }

    monkeypatch.setattr(registry, "_x_trends_colombia_async", fake_x_trends)

    async def runner():
        return registry.x_trends_colombia(limit=15)

    result = asyncio.run(runner())

    assert result["country"] == "Colombia"
    assert result["woeid"] == 368148
    assert result["count"] == 2
    assert result["limit"] == 15
    assert [item["rank"] for item in result["trends"]] == [1, 2]


def test_normalize_v1_trends_keeps_rank_and_decodes_query() -> None:
    registry = ProjectToolRegistry()
    payload = [
        {
            "trends": [
                {
                    "name": "#Colombia",
                    "tweet_volume": 12345,
                    "query": "%23Colombia",
                    "url": "https://x.com/search?q=%23Colombia",
                    "promoted_content": None,
                },
                {
                    "name": "Bogota",
                    "tweet_volume": None,
                    "query": "Bogota",
                    "url": "https://x.com/search?q=Bogota",
                    "promoted_content": None,
                },
            ]
        }
    ]

    normalized = registry._normalize_v1_trends(payload=payload, limit=10)

    assert len(normalized) == 2
    assert normalized[0]["rank"] == 1
    assert normalized[0]["query"] == "#Colombia"
    assert normalized[1]["rank"] == 2
    assert normalized[1]["query"] == "Bogota"
