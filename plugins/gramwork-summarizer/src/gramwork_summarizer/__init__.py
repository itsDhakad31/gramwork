"""gramwork-summarizer — /summarize [N] command via LLM."""

from __future__ import annotations

import re
from typing import Any

from gramwork import EventContext, Role, Router
from gramwork.llm.message import ChatMessage


class SummarizerPlugin:
    """/summarize [N] — summarize last N messages in a chat via LLM."""

    def __init__(self) -> None:
        self._router = Router()
        self._default_count = 50

        @self._router.on_message(pattern=r"^/summarize")
        async def summarize(ctx: EventContext) -> None:
            if ctx.llm is None:
                await ctx.reply("No LLM provider configured.")
                return

            # Parse optional count
            match = re.match(r"/summarize\s+(\d+)", ctx.text)
            count = int(match.group(1)) if match else self._default_count

            conv = await ctx.get_conversation()
            messages_to_summarize = conv.to_messages(limit=count)

            if not messages_to_summarize:
                await ctx.reply("No messages to summarize.")
                return

            # Build summary prompt
            transcript = "\n".join(
                f"[{m.role.value}]: {m.content}" for m in messages_to_summarize
            )
            prompt_messages = [
                ChatMessage(
                    Role.SYSTEM,
                    "You are a summarization assistant. Provide a concise summary of the conversation below.",
                ),
                ChatMessage(Role.USER, f"Summarize this conversation:\n\n{transcript}"),
            ]

            response = await ctx.llm_complete(prompt_messages)
            await ctx.reply(f"Summary ({count} messages):\n\n{response.content}")

    @property
    def name(self) -> str:
        return "summarizer"

    @property
    def router(self) -> Router:
        return self._router

    def configure(self, config: dict[str, Any]) -> None:
        self._default_count = config.get("default_count", self._default_count)

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass
