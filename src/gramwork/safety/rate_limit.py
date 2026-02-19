"""Token-bucket rate limiter exposed as middleware."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from gramwork.context import EventContext
from gramwork.types import NextFunc

logger = logging.getLogger("gramwork.safety")


@dataclass(slots=True)
class TokenBucket:
    rate: float  # tokens per second
    burst: int
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.burst)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.burst), self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware:
    """Per-chat and global token-bucket rate limiter."""

    def __init__(
        self,
        per_chat_rate: float = 5.0,
        global_rate: float = 30.0,
        burst: int = 10,
    ) -> None:
        self._per_chat_rate = per_chat_rate
        self._global_rate = global_rate
        self._burst = burst
        self._global_bucket = TokenBucket(rate=global_rate, burst=burst * 3)
        self._chat_buckets: dict[int, TokenBucket] = {}

    def _get_chat_bucket(self, chat_id: int) -> TokenBucket:
        if chat_id not in self._chat_buckets:
            self._chat_buckets[chat_id] = TokenBucket(
                rate=self._per_chat_rate, burst=self._burst
            )
        return self._chat_buckets[chat_id]

    async def __call__(self, ctx: EventContext, call_next: NextFunc) -> None:
        if not self._global_bucket.consume():
            logger.warning("Global rate limit hit")
            return

        chat_bucket = self._get_chat_bucket(ctx.chat_id)
        if not chat_bucket.consume():
            logger.warning("Per-chat rate limit hit for chat %d", ctx.chat_id)
            return

        await call_next()
