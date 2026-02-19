"""ReAct loop driving Telegram actions via LLM tool-use."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from telethon import TelegramClient, events

from gramwork.config import AgentConfig
from gramwork.llm.base import LLMProvider
from gramwork.llm.message import ChatMessage, Role, ToolCall, ToolResult
from gramwork.safety.rate_limit import TokenBucket
from gramwork.tools.base import ToolRegistry

logger = logging.getLogger("gramwork.autonomous")
audit_logger = logging.getLogger("gramwork.audit")

MAX_CONVERSATION_MESSAGES = 50


@dataclass(slots=True)
class ActionRecord:
    timestamp: str
    tool_name: str
    arguments: dict[str, Any]
    result: str
    is_error: bool
    duration_ms: float


class AutonomousBrain:
    """LLM-driven autonomous engine with a rolling conversation window.

    Dispatches tool calls through the ToolRegistry, supports both
    reactive (incoming events) and proactive (periodic) operation.
    """

    def __init__(
        self,
        client: TelegramClient,
        llm: LLMProvider,
        registry: ToolRegistry,
        config: AgentConfig,
    ) -> None:
        self._client = client
        self._llm = llm
        self._registry = registry
        self._config = config

        self._system_prompt = self._load_system_prompt()
        self._conversation: list[ChatMessage] = [
            ChatMessage(role=Role.SYSTEM, content=self._system_prompt)
        ]
        self._rate_limiter = TokenBucket(
            rate=config.outbound_rate, burst=config.outbound_burst
        )
        self._proactive_task: asyncio.Task[None] | None = None
        self._running = False
        self._lock = asyncio.Lock()

    def _load_system_prompt(self) -> str:
        if self._config.system_prompt_file:
            try:
                with open(self._config.system_prompt_file) as f:
                    return f.read().strip()
            except FileNotFoundError:
                logger.warning(
                    "System prompt file not found: %s, using default",
                    self._config.system_prompt_file,
                )
        return self._config.system_prompt

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        self._client.add_event_handler(
            self._on_incoming_event, events.NewMessage(incoming=True)
        )

        if self._config.loop_interval > 0:
            self._proactive_task = asyncio.create_task(self._proactive_loop())
        logger.info("AutonomousBrain started")

    async def stop(self) -> None:
        self._running = False
        if self._proactive_task is not None:
            self._proactive_task.cancel()
            try:
                await self._proactive_task
            except asyncio.CancelledError:
                pass
            self._proactive_task = None
        logger.info("AutonomousBrain stopped")

    async def _proactive_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._config.loop_interval)
            if not self._running:
                break
            try:
                trigger = (
                    "[SYSTEM] Periodic check-in. Review recent context and "
                    "decide if any proactive action is needed. If nothing to "
                    "do, reply with a short acknowledgement."
                )
                await self._run_react_loop(trigger)
            except Exception:
                logger.exception("Error in proactive loop")

    async def _on_incoming_event(self, event: Any) -> None:
        try:
            sender = await event.get_sender()
            sender_name = getattr(sender, "first_name", "") or "Unknown"
            sender_id = getattr(sender, "id", 0)
            chat_id = event.chat_id
            text = event.text or ""

            trigger = (
                f"[INCOMING MESSAGE]\n"
                f"From: {sender_name} (id={sender_id})\n"
                f"Chat: {chat_id}\n"
                f"Text: {text}"
            )
            await self._run_react_loop(trigger)
        except Exception:
            logger.exception("Error handling incoming event")

    async def _run_react_loop(self, trigger: str) -> None:
        """LLM -> tool calls -> execute -> feed results -> repeat
        until text-only response or max iterations."""
        async with self._lock:
            self._conversation.append(
                ChatMessage(role=Role.USER, content=trigger)
            )
            self._trim_conversation()

            tools = self._registry.get_schemas()

            for iteration in range(self._config.max_iterations):
                response = await self._llm.complete_with_tools(
                    self._conversation, tools
                )
                self._conversation.append(response)

                if not response.tool_calls:
                    logger.debug(
                        "ReAct loop done after %d iterations", iteration + 1
                    )
                    break

                for tool_call in response.tool_calls:
                    result = await self._execute_tool(tool_call)
                    self._conversation.append(result.to_message())
            else:
                logger.warning(
                    "ReAct loop hit max iterations (%d)",
                    self._config.max_iterations,
                )

            self._trim_conversation()

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        tool = self._registry.get(tool_call.name)
        if tool is None:
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                content=f"Error: unknown tool '{tool_call.name}'",
                is_error=True,
            )

        if not self._rate_limiter.consume():
            return ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                content="Error: outbound rate limit exceeded, try again later",
                is_error=True,
            )

        start = time.monotonic()
        is_error = False
        try:
            result_str = await tool.execute(**tool_call.arguments)
        except Exception as exc:
            result_str = f"Error: {exc}"
            is_error = True
            logger.error("Tool %s failed: %s", tool_call.name, exc)

        duration_ms = (time.monotonic() - start) * 1000

        audit_logger.info(
            "Tool executed: %s",
            tool_call.name,
            extra={
                "tool_name": tool_call.name,
                "tool_args": tool_call.arguments,
                "tool_result": result_str[:500],
                "is_error": is_error,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return ToolResult(
            call_id=tool_call.id,
            name=tool_call.name,
            content=result_str,
            is_error=is_error,
        )

    def _trim_conversation(self) -> None:
        """Keep system prompt + last N messages."""
        if len(self._conversation) <= MAX_CONVERSATION_MESSAGES + 1:
            return
        system = self._conversation[0]
        recent = self._conversation[-(MAX_CONVERSATION_MESSAGES):]
        self._conversation = [system] + recent
