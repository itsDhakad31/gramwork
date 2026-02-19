"""Conversation and turn data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from gramwork.llm.message import ChatMessage, Role


@dataclass(slots=True)
class Turn:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)

    def to_message(self) -> ChatMessage:
        return ChatMessage(role=self.role, content=self.content)


@dataclass(slots=True)
class Conversation:
    chat_id: int
    turns: list[Turn] = field(default_factory=list)

    def to_messages(self, *, limit: int | None = None) -> list[ChatMessage]:
        """Convert turns to ChatMessage list, optionally limited to last N."""
        turns = self.turns[-limit:] if limit else self.turns
        return [t.to_message() for t in turns]

    def add_turn(self, role: Role, content: str) -> Turn:
        turn = Turn(role=role, content=content)
        self.turns.append(turn)
        return turn
