"""Test script for x_search function (moved to tests/)."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict
from twscrape import API
from dotenv import load_dotenv
import time

# Load environment variables from auth/.env at project root
env_file = Path(__file__).parent.parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)


async def x_search(
    topic: str,
    wait_for_rate_limit: bool = False,
) -> Dict[str, Any]:
    """Search for tweets about a topic and return their content.

    Searches X (Twitter) for recent tweets about the given topic,
    filtering for tweets that contain links. Returns up to 20 tweets.

    Args:
        topic: The search topic/query
        wait_for_rate_limit: Whether to wait if rate limited

    Returns:
        Dictionary with 'text' (concatenated tweets) and 'tweets' (list)
    """

    api = API()
    # Add account from environment variables
    username = os.getenv("TWSCRAPE_USERNAME")
    password = os.getenv("TWSCRAPE_PASSWORD")
    email = os.getenv("TWSCRAPE_EMAIL_TWO")  # Using TWSCRAPE_EMAIL_TWO for the contact email
    api_key = os.getenv("TWSCRAPE_API_KEY")
    cookies_str = os.getenv("TWSCRAPE_COOKIES")

    if not all([username, password, email, api_key, cookies_str]):
        raise ValueError("Missing required TwScrape environment variables")

    await api.pool.add_account(username, password, email, api_key, cookies=cookies_str)

    # Search for tweets with improved error handling
    tweets = []
    try:
        print(f"Searching for tweets about: {topic}")
        print(f"Search query: {topic} filter:links")
        print(f"Limit: 20 tweets")
        print(f"Wait for rate limit: {wait_for_rate_limit}")
        print()
        
        search_task = api.search(f"{topic} filter:links", limit=20)
        
        count = 0
        async for tweet in search_task:
            count += 1
            print(f"Tweet #{count} retrieved (ID: {tweet.id})")
            tweets.append(tweet.rawContent)
            
        print(f"\nTotal tweets retrieved: {count}")
        
    except Exception as e:
        # Throw exception with a clear message if the search fails
        raise RuntimeError(f"Failed to search tweets for topic '{topic}': {e}")
    
    # Tweets content into a single string for summarization, using double newlines as separator
    return {"text": "\n\n---\n\n".join(tweets), "tweets": tweets}


async def main():
    """Test the x_search function."""
    print("=" * 70)
    print("TESTING x_search FUNCTION")
    print("=" * 70)
    print()
    
    # Check environment variables
    required_vars = ["TWSCRAPE_USERNAME", "TWSCRAPE_PASSWORD", "TWSCRAPE_EMAIL_TWO", 
                     "TWSCRAPE_API_KEY", "TWSCRAPE_COOKIES"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these in auth/.env file")
        return
    
    print("✓ All required environment variables are set")
    print()
    
    # Test with a simple topic  
    topic = "AI programming"
    
    print(f"Test Parameters:")
    print(f"  Topic: {topic}")
    print()
    
    try:
        print("Starting search (this may take a moment or wait for rate limits)...")
        print("-" * 70)
        
        # Add a timeout to avoid waiting too long
        result = await asyncio.wait_for(
            x_search(topic=topic, wait_for_rate_limit=False),
            timeout=120.0  # 2 minute timeout
        )
        
        print("-" * 70)
        print()
        print("=" * 70)
        print("SEARCH COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print()
        print(f"Topic: {topic}")
        print(f"Number of tweets found: {len(result.get('tweets', []))}")
        print(f"Total characters: {len(result['text'])}")
        print()
        print("=" * 70)
        print("RAW SEARCH RESULTS (Tweet Contents):")
        print("=" * 70)
        print()
        
        tweets = result.get('tweets', [])
        if tweets:
            for i, tweet in enumerate(tweets, 1):
                print(f"{'='*70}")
                print(f"TWEET #{i}")
                print(f"{'='*70}")
                print(tweet.strip())
                print()
        else:
            print("(No tweets found)")
        
        print("=" * 70)
        
    except asyncio.TimeoutError:
        print()
        print("❌ TIMEOUT: The function is waiting for rate limits to clear.")
        print("   The X/Twitter API account needs time before it can make more requests.")
        print("   This is normal behavior - the account will be available again soon.")
        print()
        print("TIP: You can try again in a few minutes, or the function will automatically")
        print("     wait for the account to become available when called through MCP.")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        
    except RuntimeError as e:
        print(f"❌ Search Error: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
