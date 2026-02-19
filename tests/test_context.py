"""Tests for EventContext."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from gramwork.context import EventContext
from gramwork.llm.message import ChatMessage, Role
from gramwork.state.memory import MemoryBackend


@pytest.fixture
def mock_event():
    event = MagicMock()
    event.text = "hello world"
    event.raw_text = "hello world"
    event.chat_id = 42
    event.sender_id = 100
    event.is_private = True
    event.is_group = False
    event.reply = AsyncMock(return_value=None)
    event.respond = AsyncMock(return_value=None)
    event.delete = AsyncMock(return_value=None)
    return event


def test_text_shortcuts(mock_event):
    ctx = EventContext(mock_event)
    assert ctx.text == "hello world"
    assert ctx.chat_id == 42
    assert ctx.sender_id == 100
    assert ctx.is_private is True
    assert ctx.is_group is False


async def test_reply(mock_event):
    ctx = EventContext(mock_event)
    await ctx.reply("pong")
    mock_event.reply.assert_awaited_once_with("pong")


async def test_respond(mock_event):
    ctx = EventContext(mock_event)
    await ctx.respond("broadcast")
    mock_event.respond.assert_awaited_once_with("broadcast")


async def test_state_shortcuts(mock_event):
    backend = MemoryBackend()
    ctx = EventContext(mock_event, state=backend)

    conv = await ctx.get_conversation()
    assert conv.chat_id == 42

    turn = await ctx.save_turn(Role.USER, "test")
    assert turn.content == "test"


async def test_no_state_raises(mock_event):
    ctx = EventContext(mock_event)
    with pytest.raises(RuntimeError, match="No state backend"):
        await ctx.get_conversation()


async def test_no_llm_raises(mock_event):
    ctx = EventContext(mock_event)
    with pytest.raises(RuntimeError, match="No LLM provider"):
        await ctx.llm_complete([])


async def test_llm_complete(mock_event):
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=ChatMessage(Role.ASSISTANT, "response")
    )
    ctx = EventContext(mock_event, llm=mock_llm)
    result = await ctx.llm_complete([ChatMessage(Role.USER, "hi")])
    assert result.content == "response"


def test_extra_dict(mock_event):
    ctx = EventContext(mock_event)
    ctx.extra["key"] = "value"
    assert ctx.extra["key"] == "value"
