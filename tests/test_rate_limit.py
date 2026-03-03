from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

from core.rate_limit import DailyRateLimiter


def test_daily_rate_limiter_blocks_after_limit(tmp_path: Path) -> None:
    limiter = DailyRateLimiter(tmp_path / "rl.sqlite")
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)

    r1 = limiter.consume(scope="send_ws_msg", limit=2, amount=1, now=now)
    assert r1.allowed is True
    assert r1.used == 1
    assert r1.remaining == 1

    r2 = limiter.consume(scope="send_ws_msg", limit=2, amount=1, now=now)
    assert r2.allowed is True
    assert r2.used == 2
    assert r2.remaining == 0

    r3 = limiter.consume(scope="send_ws_msg", limit=2, amount=1, now=now)
    assert r3.allowed is False
    assert r3.used == 2
