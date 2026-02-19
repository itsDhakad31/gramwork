"""Tests for LLM types."""

from gramwork.llm.message import ChatMessage, Role


def test_chat_message():
    msg = ChatMessage(Role.USER, "hello")
    assert msg.role == Role.USER
    assert msg.content == "hello"


def test_to_dict():
    msg = ChatMessage(Role.ASSISTANT, "hi")
    d = msg.to_dict()
    assert d == {"role": "assistant", "content": "hi"}


def test_role_values():
    assert Role.SYSTEM.value == "system"
    assert Role.USER.value == "user"
    assert Role.ASSISTANT.value == "assistant"
