"""Tests for state backends."""

import pytest

from gramwork.llm.message import Role
from gramwork.state.memory import MemoryBackend
from gramwork.state.models import Conversation, Turn


@pytest.fixture
def backend():
    return MemoryBackend()


async def test_get_conversation_creates_new(backend):
    conv = await backend.get_conversation(123)
    assert isinstance(conv, Conversation)
    assert conv.chat_id == 123
    assert conv.turns == []


async def test_save_and_retrieve_turn(backend):
    turn = Turn(role=Role.USER, content="hello")
    await backend.save_turn(123, turn)

    conv = await backend.get_conversation(123)
    assert len(conv.turns) == 1
    assert conv.turns[0].content == "hello"


async def test_kv_store(backend):
    assert await backend.get_value(1, "key") is None

    await backend.set_value(1, "key", "value")
    assert await backend.get_value(1, "key") == "value"

    await backend.set_value(1, "key", "updated")
    assert await backend.get_value(1, "key") == "updated"


async def test_conversation_to_messages():
    conv = Conversation(chat_id=1)
    conv.add_turn(Role.USER, "hi")
    conv.add_turn(Role.ASSISTANT, "hello")
    conv.add_turn(Role.USER, "bye")

    msgs = conv.to_messages()
    assert len(msgs) == 3

    limited = conv.to_messages(limit=2)
    assert len(limited) == 2
    assert limited[0].content == "hello"


async def test_close(backend):
    await backend.set_value(1, "k", "v")
    await backend.close()
    # After close, data is cleared
    assert await backend.get_value(1, "k") is None
