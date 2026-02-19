"""Telethon client wrapper + lifecycle management."""

from __future__ import annotations

from telethon import TelegramClient
from telethon.sessions import StringSession

from gramwork.config import TelegramConfig


class Agent:
    """Wraps TelegramClient for testability and clean lifecycle."""

    def __init__(
        self,
        config: TelegramConfig,
        *,
        session: StringSession | None = None,
    ) -> None:
        self._config = config
        self._session = session
        self._client: TelegramClient | None = None

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            raise RuntimeError("Agent not started — call start() first")
        return self._client

    async def start(self) -> TelegramClient:
        """Create and connect the Telethon client."""
        session_arg: str | StringSession = (
            self._session if self._session is not None else self._config.session_name
        )
        self._client = TelegramClient(
            session_arg,
            self._config.api_id,
            self._config.api_hash,
        )
        await self._client.start(phone=self._config.phone or None)  # type: ignore[arg-type]
        return self._client

    async def stop(self) -> None:
        """Disconnect the Telethon client."""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def run_until_disconnected(self) -> None:
        """Block until the client disconnects."""
        await self.client.run_until_disconnected()  # type: ignore[misc]
