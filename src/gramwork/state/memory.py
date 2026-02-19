"""In-memory state backend (default, development use)."""

from __future__ import annotations

from typing import Any

from gramwork.state.models import Conversation, Turn


class MemoryBackend:
    """Dict-based in-memory state backend."""

    def __init__(self) -> None:
        self._conversations: dict[int, Conversation] = {}
        self._kv: dict[int, dict[str, Any]] = {}

    async def get_conversation(self, chat_id: int) -> Conversation:
        if chat_id not in self._conversations:
            self._conversations[chat_id] = Conversation(chat_id=chat_id)
        return self._conversations[chat_id]

    async def save_turn(self, chat_id: int, turn: Turn) -> None:
        conv = await self.get_conversation(chat_id)
        conv.turns.append(turn)

    async def get_value(self, chat_id: int, key: str) -> Any:
        return self._kv.get(chat_id, {}).get(key)

    async def set_value(self, chat_id: int, key: str, value: Any) -> None:
        self._kv.setdefault(chat_id, {})[key] = value

    async def close(self) -> None:
        self._conversations.clear()
        self._kv.clear()
