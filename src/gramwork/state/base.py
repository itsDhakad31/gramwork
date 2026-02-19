"""State backend protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from gramwork.state.models import Conversation, Turn


@runtime_checkable
class StateBackend(Protocol):
    """Protocol for conversation state persistence."""

    async def get_conversation(self, chat_id: int) -> Conversation:
        """Get or create a conversation for a chat."""
        ...

    async def save_turn(self, chat_id: int, turn: Turn) -> None:
        """Persist a single turn to a conversation."""
        ...

    async def get_value(self, chat_id: int, key: str) -> Any:
        """Get a key-value entry scoped to a chat."""
        ...

    async def set_value(self, chat_id: int, key: str, value: Any) -> None:
        """Set a key-value entry scoped to a chat."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...
