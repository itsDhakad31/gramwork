"""Telegram tools wrapping Telethon for the autonomous agent."""

from __future__ import annotations

import json
from typing import Any

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest

from gramwork.tools.base import ToolRegistry, ToolSpec


def _json(data: Any) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


def register_telegram_tools(
    client: TelegramClient,
    registry: ToolRegistry,
    *,
    allowed: list[str] | None = None,
) -> None:
    """Register Telegram tools. If *allowed* is set, only those are added."""
    tools = _build_telegram_tools(client)
    for tool in tools:
        if allowed is None or tool.name in allowed:
            registry.register(tool)


def _build_telegram_tools(client: TelegramClient) -> list[ToolSpec]:

    async def send_message(chat_id: int | str, text: str) -> str:
        msg = await client.send_message(chat_id, text)
        return _json({"message_id": msg.id, "chat_id": msg.chat_id, "text": msg.text})

    async def reply_message(chat_id: int | str, message_id: int, text: str) -> str:
        msg = await client.send_message(chat_id, text, reply_to=message_id)
        return _json({"message_id": msg.id, "chat_id": msg.chat_id, "text": msg.text})

    async def forward_message(
        from_chat_id: int | str, message_id: int, to_chat_id: int | str
    ) -> str:
        msgs = await client.forward_messages(to_chat_id, message_id, from_chat_id)
        forwarded = msgs if isinstance(msgs, list) else [msgs]
        return _json({"forwarded": [{"id": m.id, "chat_id": m.chat_id} for m in forwarded]})

    async def delete_message(chat_id: int | str, message_id: int) -> str:
        result = await client.delete_messages(chat_id, [message_id])
        return _json({"deleted": bool(result)})

    async def get_messages(chat_id: int | str, limit: int = 20) -> str:
        limit = min(limit, 100)
        msgs = await client.get_messages(chat_id, limit=limit)
        return _json([
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "text": m.text,
                "date": m.date,
            }
            for m in msgs
        ])

    async def search_messages(chat_id: int | str, query: str, limit: int = 10) -> str:
        limit = min(limit, 50)
        msgs = await client.get_messages(chat_id, limit=limit, search=query)
        return _json([
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "text": m.text,
                "date": m.date,
            }
            for m in msgs
        ])

    async def get_dialogs(limit: int = 20) -> str:
        limit = min(limit, 100)
        dialogs = await client.get_dialogs(limit=limit)
        return _json([
            {
                "id": d.id,
                "name": d.name,
                "unread_count": d.unread_count,
                "is_group": d.is_group,
                "is_channel": d.is_channel,
            }
            for d in dialogs
        ])

    async def get_chat_info(chat_id: int | str) -> str:
        entity = await client.get_entity(chat_id)
        info: dict[str, Any] = {"id": entity.id}
        for attr in ("title", "username", "first_name", "last_name", "phone"):
            if hasattr(entity, attr):
                info[attr] = getattr(entity, attr)
        return _json(info)

    async def get_chat_members(chat_id: int | str, limit: int = 50) -> str:
        limit = min(limit, 200)
        members = await client.get_participants(chat_id, limit=limit)
        return _json([
            {
                "id": m.id,
                "username": m.username,
                "first_name": m.first_name,
                "last_name": m.last_name,
            }
            for m in members
        ])

    async def get_me() -> str:
        me = await client.get_me()
        return _json({
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "phone": me.phone,
        })

    async def join_chat(chat_id: int | str) -> str:
        entity = await client.get_entity(chat_id)
        await client(JoinChannelRequest(entity))
        return _json({"joined": True, "chat_id": entity.id})

    async def leave_chat(chat_id: int | str) -> str:
        entity = await client.get_entity(chat_id)
        await client(LeaveChannelRequest(entity))
        return _json({"left": True, "chat_id": entity.id})

    async def send_file(
        chat_id: int | str, file_path: str, caption: str = ""
    ) -> str:
        msg = await client.send_file(chat_id, file_path, caption=caption)
        return _json({"message_id": msg.id, "chat_id": msg.chat_id})

    _CHAT_ID = {
        "type": ["integer", "string"],
        "description": "Chat ID or username",
    }

    return [
        ToolSpec(
            name="send_message",
            description="Send a text message to a chat.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "text": {
                        "type": "string",
                        "description": "Message text to send",
                    },
                },
                "required": ["chat_id", "text"],
            },
            _fn=send_message,
        ),
        ToolSpec(
            name="reply_message",
            description="Reply to a specific message in a chat.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "message_id": {
                        "type": "integer",
                        "description": "ID of message to reply to",
                    },
                    "text": {
                        "type": "string",
                        "description": "Reply text",
                    },
                },
                "required": ["chat_id", "message_id", "text"],
            },
            _fn=reply_message,
        ),
        ToolSpec(
            name="forward_message",
            description="Forward a message from one chat to another.",
            parameters={
                "type": "object",
                "properties": {
                    "from_chat_id": {
                        "type": ["integer", "string"],
                        "description": "Source chat",
                    },
                    "message_id": {
                        "type": "integer",
                        "description": "Message ID to forward",
                    },
                    "to_chat_id": {
                        "type": ["integer", "string"],
                        "description": "Destination chat",
                    },
                },
                "required": [
                    "from_chat_id", "message_id", "to_chat_id",
                ],
            },
            _fn=forward_message,
        ),
        ToolSpec(
            name="delete_message",
            description="Delete a message in a chat.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "message_id": {
                        "type": "integer",
                        "description": "Message ID to delete",
                    },
                },
                "required": ["chat_id", "message_id"],
            },
            _fn=delete_message,
        ),
        ToolSpec(
            name="get_messages",
            description="Read recent messages from a chat.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "limit": {
                        "type": "integer",
                        "description": "Max messages (default 20)",
                    },
                },
                "required": ["chat_id"],
            },
            _fn=get_messages,
        ),
        ToolSpec(
            name="search_messages",
            description="Search messages in a chat by text query.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 10)",
                    },
                },
                "required": ["chat_id", "query"],
            },
            _fn=search_messages,
        ),
        ToolSpec(
            name="get_dialogs",
            description="List recent chats/dialogs.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max dialogs (default 20)",
                    },
                },
                "required": [],
            },
            _fn=get_dialogs,
        ),
        ToolSpec(
            name="get_chat_info",
            description="Get information about a chat or user.",
            parameters={
                "type": "object",
                "properties": {"chat_id": _CHAT_ID},
                "required": ["chat_id"],
            },
            _fn=get_chat_info,
        ),
        ToolSpec(
            name="get_chat_members",
            description="Get members of a group or channel.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "limit": {
                        "type": "integer",
                        "description": "Max members (default 50)",
                    },
                },
                "required": ["chat_id"],
            },
            _fn=get_chat_members,
        ),
        ToolSpec(
            name="get_me",
            description="Get info about the logged-in user.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            _fn=get_me,
        ),
        ToolSpec(
            name="join_chat",
            description="Join a channel or group.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": ["integer", "string"],
                        "description": "Chat/channel to join",
                    },
                },
                "required": ["chat_id"],
            },
            _fn=join_chat,
        ),
        ToolSpec(
            name="leave_chat",
            description="Leave a channel or group.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": ["integer", "string"],
                        "description": "Chat/channel to leave",
                    },
                },
                "required": ["chat_id"],
            },
            _fn=leave_chat,
        ),
        ToolSpec(
            name="send_file",
            description="Send a file to a chat with optional caption.",
            parameters={
                "type": "object",
                "properties": {
                    "chat_id": _CHAT_ID,
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to send",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional caption",
                    },
                },
                "required": ["chat_id", "file_path"],
            },
            _fn=send_file,
        ),
    ]
