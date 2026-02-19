"""Tests for rate limiting."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gramwork.context import EventContext
from gramwork.safety.rate_limit import RateLimitMiddleware, TokenBucket


def test_token_bucket_allows():
    bucket = TokenBucket(rate=10.0, burst=5)
    for _ in range(5):
        assert bucket.consume() is True


def test_token_bucket_depletes():
    bucket = TokenBucket(rate=1.0, burst=2)
    assert bucket.consume() is True
    assert bucket.consume() is True
    assert bucket.consume() is False


async def test_rate_limit_middleware_allows():
    mw = RateLimitMiddleware(per_chat_rate=10.0, global_rate=100.0, burst=10)
    event = MagicMock()
    event.chat_id = 1
    ctx = EventContext(event)
    handler = AsyncMock()

    await mw(ctx, handler)
    handler.assert_awaited_once()


async def test_rate_limit_middleware_blocks_after_burst():
    mw = RateLimitMiddleware(per_chat_rate=1.0, global_rate=100.0, burst=2)
    event = MagicMock()
    event.chat_id = 1
    handler = AsyncMock()

    # First 2 should pass
    for _ in range(2):
        ctx = EventContext(event)
        await mw(ctx, handler)

    # Third should be blocked
    ctx = EventContext(event)
    handler.reset_mock()
    await mw(ctx, handler)
    handler.assert_not_awaited()
