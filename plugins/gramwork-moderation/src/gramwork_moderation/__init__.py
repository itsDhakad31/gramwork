"""gramwork-moderation — Regex + optional LLM content filtering."""

from __future__ import annotations

import logging
from typing import Any

from gramwork import EventContext, Router
from gramwork.safety.filters import ContentFilter, ContentFilterMiddleware

logger = logging.getLogger("gramwork.plugins.moderation")


class ModerationPlugin:
    """Auto-delete messages matching blocked patterns."""

    def __init__(self) -> None:
        self._router = Router()
        self._filter_mw = ContentFilterMiddleware(auto_delete=True)
        self._patterns: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "moderation"

    @property
    def router(self) -> Router:
        return self._router

    def configure(self, config: dict[str, Any]) -> None:
        self._patterns = config.get("filters", [])
        auto_delete = config.get("auto_delete", True)
        self._filter_mw = ContentFilterMiddleware(auto_delete=auto_delete)

        for f in self._patterns:
            name = f.get("name", "unnamed")
            patterns = f.get("patterns", [])
            self._filter_mw.add_patterns(name, patterns)

    async def on_startup(self) -> None:
        logger.info(
            "Moderation plugin started with %d filters",
            len(self._filter_mw._filters),
        )

    async def on_shutdown(self) -> None:
        pass
