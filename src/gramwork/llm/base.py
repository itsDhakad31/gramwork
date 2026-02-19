"""LLM provider protocol."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from gramwork.llm.message import ChatMessage


@runtime_checkable
class LLMProvider(Protocol):

    async def complete(self, messages: list[ChatMessage]) -> ChatMessage: ...

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]: ...

    async def complete_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ChatMessage: ...
