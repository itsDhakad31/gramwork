"""OpenAI-compatible LLM provider."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import aiohttp

from gramwork.exceptions import LLMError
from gramwork.llm.message import ChatMessage, Role, ToolCall

logger = logging.getLogger("gramwork.llm.openai_compat")


@dataclass(slots=True)
class OpenAICompatConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    extra_headers: dict[str, str] = field(default_factory=dict)


class OpenAICompatProvider:
    """Works with any service implementing the OpenAI /chat/completions API
    (OpenAI, Groq, Together, vLLM, LM Studio, etc.)."""

    def __init__(self, config: OpenAICompatConfig | None = None) -> None:
        self._config = config or OpenAICompatConfig()
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                **self._config.extra_headers,
            }
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @property
    def _url(self) -> str:
        return f"{self._config.base_url.rstrip('/')}/chat/completions"

    def _build_payload(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        return payload

    async def complete(self, messages: list[ChatMessage]) -> ChatMessage:
        session = self._get_session()
        payload = self._build_payload(messages)

        try:
            async with session.post(self._url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"OpenAI-compat error {resp.status}: {body}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise LLMError(f"OpenAI-compat connection error: {exc}") from exc

        choice = data["choices"][0]["message"]
        return ChatMessage(
            role=Role.ASSISTANT, content=choice.get("content", "") or ""
        )

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        session = self._get_session()
        payload = self._build_payload(messages, stream=True)

        try:
            async with session.post(self._url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"OpenAI-compat error {resp.status}: {body}"
                    )
                async for line in resp.content:
                    text = line.decode("utf-8").strip()
                    if not text or not text.startswith("data: "):
                        continue
                    text = text[len("data: "):]
                    if text == "[DONE]":
                        break
                    chunk = json.loads(text)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
        except aiohttp.ClientError as exc:
            raise LLMError(f"OpenAI-compat connection error: {exc}") from exc

    async def complete_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ChatMessage:
        session = self._get_session()
        payload = self._build_payload(messages, tools=tools)

        try:
            async with session.post(self._url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"OpenAI-compat error {resp.status}: {body}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise LLMError(f"OpenAI-compat connection error: {exc}") from exc

        choice = data["choices"][0]["message"]
        content = choice.get("content", "") or ""
        raw_tool_calls = choice.get("tool_calls", [])

        tool_calls: list[ToolCall] | None = None
        if raw_tool_calls:
            tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    name=fn.get("name", ""),
                    arguments=args,
                ))

        return ChatMessage(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls if tool_calls else None,
        )
