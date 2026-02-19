"""Content safety filters — regex-based and optional LLM-based."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from gramwork.context import EventContext
from gramwork.types import NextFunc

logger = logging.getLogger("gramwork.safety")


@dataclass(slots=True)
class ContentFilter:
    """A named filter with compiled regex patterns."""
    name: str
    patterns: list[re.Pattern[str]] = field(default_factory=list)

    @classmethod
    def from_strings(cls, name: str, patterns: list[str]) -> ContentFilter:
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        return cls(name=name, patterns=compiled)

    def matches(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)


class ContentFilterMiddleware:
    """Middleware that blocks messages matching any registered filter."""

    def __init__(self, *, auto_delete: bool = False) -> None:
        self._filters: list[ContentFilter] = []
        self._auto_delete = auto_delete

    def add_filter(self, content_filter: ContentFilter) -> None:
        self._filters.append(content_filter)

    def add_patterns(self, name: str, patterns: list[str]) -> None:
        self._filters.append(ContentFilter.from_strings(name, patterns))

    async def __call__(self, ctx: EventContext, call_next: NextFunc) -> None:
        text = ctx.text
        if not text:
            await call_next()
            return

        for f in self._filters:
            if f.matches(text):
                logger.warning(
                    "Content filter '%s' triggered in chat %d",
                    f.name,
                    ctx.chat_id,
                )
                if self._auto_delete:
                    try:
                        await ctx.delete()
                    except Exception:
                        logger.exception("Failed to auto-delete filtered message")
                return

        await call_next()
