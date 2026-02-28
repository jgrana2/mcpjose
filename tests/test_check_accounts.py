"""Check twscrape account status."""
import asyncio
from twscrape import API


async def main():
    api = API()
    accounts = await api.pool.accounts_info()
    print("Account Status:")
    print("=" * 60)
    for acc in accounts:
        print(f"Username: {acc.get('username', 'N/A')}")
        print(f"Active: {acc.get('active', 'N/A')}")
        print(f"Last Used: {acc.get('last_used', 'N/A')}")
        print(f"Locks: {acc.get('locks', 'N/A')}")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
