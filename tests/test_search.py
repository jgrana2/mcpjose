#!/usr/bin/env python3
"""Test search functionality."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from providers.search import SearchFactory, DuckDuckGoProvider, GooglePSEProvider


def test_search():
    """Test search providers."""
    print("=" * 60)
    print("SEARCH PROVIDER TESTS")
    print("=" * 60)

    # Test DuckDuckGo
    print("\n1. Testing DuckDuckGo...")
    provider = SearchFactory.create("ddgs")
    result = provider.search("Python programming", max_results=3)

    if "results" in result:
        print(f"✓ Found {len(result['results'])} results")
        if result["results"]:
            print(f"  First: {result['results'][0]['title']}")
    elif "error" in result:
        print(f"⚠ Error: {result['error']}")

    # Test Google PSE if credentials available
    if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CSE_ID"):
        print("\n2. Testing Google PSE...")
        provider = SearchFactory.create("pse")
        result = provider.search("Python programming", max_results=3)

        if "results" in result:
            print(f"✓ Found {len(result['results'])} results")
        elif "error" in result:
            print(f"⚠ Error: {result['error']}")
    else:
        print("\n2. Skipping Google PSE (no credentials)")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_search()
