"""EventContext — the 'request' object passed to every handler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gramwork.llm.message import ChatMessage, Role
from gramwork.state.models import Conversation, Turn

if TYPE_CHECKING:
    from gramwork.llm.base import LLMProvider
    from gramwork.state.base import StateBackend


class EventContext:
    """Wraps a Telethon event via composition, providing shortcuts and access to
    framework services (LLM, state)."""

    __slots__ = ("event", "llm", "state", "extra", "_app")

    def __init__(
        self,
        event: Any,
        *,
        llm: LLMProvider | None = None,
        state: StateBackend | None = None,
        app: Any = None,
    ) -> None:
        self.event = event
        self.llm = llm
        self.state = state
        self.extra: dict[str, Any] = {}
        self._app = app

    # ── Telethon event shortcuts ──

    @property
    def text(self) -> str:
        return getattr(self.event, "text", "") or ""

    @property
    def raw_text(self) -> str:
        return getattr(self.event, "raw_text", "") or ""

    @property
    def chat_id(self) -> int:
        return self.event.chat_id  # type: ignore[no-any-return]

    @property
    def sender_id(self) -> int | None:
        return getattr(self.event, "sender_id", None)

    @property
    def is_private(self) -> bool:
        return getattr(self.event, "is_private", False)

    @property
    def is_group(self) -> bool:
        return getattr(self.event, "is_group", False)

    @property
    def message(self) -> Any:
        return getattr(self.event, "message", None)

    async def reply(self, text: str, **kwargs: Any) -> Any:
        """Reply to the triggering message."""
        return await self.event.reply(text, **kwargs)

    async def respond(self, text: str, **kwargs: Any) -> Any:
        """Send a message to the chat (not as reply)."""
        return await self.event.respond(text, **kwargs)

    async def delete(self) -> None:
        """Delete the triggering message."""
        await self.event.delete()

    # ── State shortcuts ──

    async def get_conversation(self) -> Conversation:
        """Get or create the conversation for this chat."""
        if self.state is None:
            raise RuntimeError("No state backend configured")
        return await self.state.get_conversation(self.chat_id)

    async def save_turn(self, role: Role, content: str) -> Turn:
        """Save a turn to the current chat's conversation."""
        if self.state is None:
            raise RuntimeError("No state backend configured")
        turn = Turn(role=role, content=content)
        await self.state.save_turn(self.chat_id, turn)
        return turn

    # ── LLM shortcuts ──

    async def llm_complete(self, messages: list[ChatMessage]) -> ChatMessage:
        """Call the LLM provider's complete method."""
        if self.llm is None:
            raise RuntimeError("No LLM provider configured")
        return await self.llm.complete(messages)
