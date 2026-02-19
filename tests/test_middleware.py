"""Tests for middleware stack."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gramwork.context import EventContext
from gramwork.middleware import MiddlewareStack


@pytest.fixture
def mock_ctx():
    event = MagicMock()
    event.chat_id = 1
    return EventContext(event)


async def test_empty_stack(mock_ctx):
    stack = MiddlewareStack()
    handler = AsyncMock()
    await stack.execute(mock_ctx, handler)
    handler.assert_awaited_once()


async def test_single_middleware(mock_ctx):
    stack = MiddlewareStack()
    order = []

    async def mw(ctx, call_next):
        order.append("before")
        await call_next()
        order.append("after")

    stack.add(mw)

    async def handler():
        order.append("handler")

    await stack.execute(mock_ctx, handler)
    assert order == ["before", "handler", "after"]


async def test_multiple_middleware(mock_ctx):
    stack = MiddlewareStack()
    order = []

    async def mw1(ctx, call_next):
        order.append("mw1-before")
        await call_next()
        order.append("mw1-after")

    async def mw2(ctx, call_next):
        order.append("mw2-before")
        await call_next()
        order.append("mw2-after")

    stack.add(mw1)
    stack.add(mw2)

    async def handler():
        order.append("handler")

    await stack.execute(mock_ctx, handler)
    assert order == ["mw1-before", "mw2-before", "handler", "mw2-after", "mw1-after"]


async def test_middleware_can_short_circuit(mock_ctx):
    stack = MiddlewareStack()

    async def blocking_mw(ctx, call_next):
        # Don't call call_next — short circuit
        pass

    stack.add(blocking_mw)
    handler = AsyncMock()
    await stack.execute(mock_ctx, handler)
    handler.assert_not_awaited()
