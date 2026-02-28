#!/usr/bin/env python3
"""CLI entry point for web search (Google or DuckDuckGo)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from providers.search import SearchFactory


def main():
    parser = argparse.ArgumentParser(
        description="Web search using DuckDuckGo or Google (PSE)"
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--backend",
        choices=["ddgs", "pse"],
        default="ddgs",
        help="Search backend: ddgs=DuckDuckGo, pse=Google (PSE/Googling)",
    )
    parser.add_argument("--max-results", type=int, default=5, help="Maximum results")
    args = parser.parse_args()

    provider = SearchFactory.create(args.backend)
    result = provider.search(args.query, max_results=args.max_results)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if "message" in result:
        print(result["message"])
    else:
        print(f"Web search results for: {args.query} (backend: {args.backend})")
        for i, item in enumerate(result.get("results", []), 1):
            print(f"\n{i}. {item['title']}")
            print(f"   URL: {item['url']}")
            print(f"   {item['snippet'][:150]}...")


if __name__ == "__main__":
    main()
