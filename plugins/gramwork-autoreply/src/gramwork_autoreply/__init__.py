"""gramwork-autoreply — AI-powered conversational replies."""

from __future__ import annotations

from typing import Any

from gramwork import EventContext, Role, Router


class AutoReplyPlugin:
    """AI-powered conversational replies in private/group chats."""

    def __init__(self) -> None:
        self._router = Router()
        self._system_prompt = "You are a helpful assistant."
        self._private_only = True

        @self._router.on_message()
        async def auto_reply(ctx: EventContext) -> None:
            if self._private_only and not ctx.is_private:
                return
            if not ctx.text or ctx.text.startswith("/"):
                return
            if ctx.llm is None:
                return

            conv = await ctx.get_conversation()
            conv.add_turn(Role.USER, ctx.text)

            from gramwork.llm.message import ChatMessage

            messages = [ChatMessage(Role.SYSTEM, self._system_prompt)]
            messages.extend(conv.to_messages(limit=20))

            response = await ctx.llm_complete(messages)
            conv.add_turn(Role.ASSISTANT, response.content)
            await ctx.save_turn(Role.USER, ctx.text)
            await ctx.save_turn(Role.ASSISTANT, response.content)
            await ctx.reply(response.content)

    @property
    def name(self) -> str:
        return "autoreply"

    @property
    def router(self) -> Router:
        return self._router

    def configure(self, config: dict[str, Any]) -> None:
        self._system_prompt = config.get("system_prompt", self._system_prompt)
        self._private_only = config.get("private_only", self._private_only)

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass
