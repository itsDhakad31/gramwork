"""Tests for content safety filters."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gramwork.context import EventContext
from gramwork.safety.filters import ContentFilter, ContentFilterMiddleware


def test_content_filter_matches():
    f = ContentFilter.from_strings("spam", [r"buy\s+now", r"free money"])
    assert f.matches("Click to buy now!") is True
    assert f.matches("Get free money today") is True
    assert f.matches("Hello world") is False


async def test_filter_middleware_blocks():
    mw = ContentFilterMiddleware()
    mw.add_patterns("spam", [r"buy now"])

    event = MagicMock()
    event.text = "buy now!"
    event.chat_id = 1
    ctx = EventContext(event)
    handler = AsyncMock()

    await mw(ctx, handler)
    handler.assert_not_awaited()


async def test_filter_middleware_passes_clean():
    mw = ContentFilterMiddleware()
    mw.add_patterns("spam", [r"buy now"])

    event = MagicMock()
    event.text = "hello friend"
    event.chat_id = 1
    ctx = EventContext(event)
    handler = AsyncMock()

    await mw(ctx, handler)
    handler.assert_awaited_once()


async def test_filter_middleware_auto_delete():
    mw = ContentFilterMiddleware(auto_delete=True)
    mw.add_patterns("spam", [r"spam"])

    event = MagicMock()
    event.text = "this is spam"
    event.chat_id = 1
    event.delete = AsyncMock()
    ctx = EventContext(event)
    handler = AsyncMock()

    await mw(ctx, handler)
    event.delete.assert_awaited_once()
    handler.assert_not_awaited()
