"""SQLite state backend (optional — requires aiosqlite)."""

from __future__ import annotations

import json
from typing import Any

try:
    import aiosqlite
except ImportError as e:
    raise ImportError(
        "SqliteBackend requires aiosqlite. Install with: pip install gramwork[sqlite]"
    ) from e

from gramwork.llm.message import Role
from gramwork.state.models import Conversation, Turn


class SqliteBackend:
    """Persistent state backend using SQLite via aiosqlite."""

    def __init__(self, db_path: str = "gramwork_state.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self._db_path)
            await self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_turns_chat ON turns(chat_id);

                CREATE TABLE IF NOT EXISTS kv (
                    chat_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (chat_id, key)
                );
                """
            )
            await self._db.commit()
        return self._db

    async def get_conversation(self, chat_id: int) -> Conversation:
        db = await self._ensure_db()
        cursor = await db.execute(
            "SELECT role, content, timestamp, metadata FROM turns WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        )
        rows = await cursor.fetchall()
        turns = [
            Turn(
                role=Role(row[0]),
                content=row[1],
                metadata=json.loads(row[3]) if row[3] else {},
            )
            for row in rows
        ]
        return Conversation(chat_id=chat_id, turns=turns)

    async def save_turn(self, chat_id: int, turn: Turn) -> None:
        db = await self._ensure_db()
        await db.execute(
            "INSERT INTO turns (chat_id, role, content, timestamp, metadata)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                chat_id,
                turn.role.value,
                turn.content,
                turn.timestamp.isoformat(),
                json.dumps(turn.metadata, default=str),
            ),
        )
        await db.commit()

    async def get_value(self, chat_id: int, key: str) -> Any:
        db = await self._ensure_db()
        cursor = await db.execute(
            "SELECT value FROM kv WHERE chat_id = ? AND key = ?",
            (chat_id, key),
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def set_value(self, chat_id: int, key: str, value: Any) -> None:
        db = await self._ensure_db()
        await db.execute(
            "INSERT OR REPLACE INTO kv (chat_id, key, value) VALUES (?, ?, ?)",
            (chat_id, key, json.dumps(value, default=str)),
        )
        await db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
