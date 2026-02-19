"""Ollama LLM provider with custom base_url support."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import aiohttp

from gramwork.exceptions import LLMError
from gramwork.llm.message import ChatMessage, Role, ToolCall

logger = logging.getLogger("gramwork.llm.ollama")

_FUNC_CALL_RE = re.compile(
    r"<function_calls?>(.*?)</function_calls?>", re.DOTALL
)
_INVOKE_RE = re.compile(
    r'<invoke\s+name="([^"]+)"[^>]*>(.*?)</invoke>', re.DOTALL
)
_PARAM_RE = re.compile(
    r'<parameter\s+name="([^"]+)"[^>]*>(.*?)</parameter>', re.DOTALL
)


def _parse_xml_tool_calls(content: str) -> list[ToolCall] | None:
    """Extract tool calls from XML blocks in content text.

    Some models emit tool calls as XML instead of structured tool_calls.
    """
    block_match = _FUNC_CALL_RE.search(content)
    if not block_match:
        return None

    block = block_match.group(1)
    invocations = _INVOKE_RE.findall(block)
    if not invocations:
        return None

    calls: list[ToolCall] = []
    for i, (name, body) in enumerate(invocations):
        params = _PARAM_RE.findall(body)
        arguments: dict[str, Any] = {}
        for pname, pvalue in params:
            try:
                arguments[pname] = json.loads(pvalue)
            except (json.JSONDecodeError, ValueError):
                arguments[pname] = pvalue
        calls.append(ToolCall(id=f"call_{i}", name=name, arguments=arguments))

    return calls if calls else None


def _strip_xml_tool_calls(content: str) -> str:
    return _FUNC_CALL_RE.sub("", content).strip()


@dataclass(slots=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"
    temperature: float = 0.7
    timeout: float = 120.0
    options: dict[str, Any] = field(default_factory=dict)


class OllamaProvider:
    """Ollama provider via /api/chat. Handles both native tool_calls
    and XML-in-content tool calls (DeepSeek, etc.)."""

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self._config = config or OllamaConfig()
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

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
            "stream": stream,
            "options": {
                "temperature": self._config.temperature,
                **self._config.options,
            },
        }
        if tools:
            payload["tools"] = tools
        return payload

    async def complete(self, messages: list[ChatMessage]) -> ChatMessage:
        session = self._get_session()
        url = f"{self._config.base_url.rstrip('/')}/api/chat"
        payload = self._build_payload(messages)

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"Ollama API error {resp.status}: {body}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise LLMError(f"Ollama connection error: {exc}") from exc

        msg = data.get("message", {})
        return ChatMessage(
            role=Role.ASSISTANT, content=msg.get("content", "")
        )

    async def stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str]:
        session = self._get_session()
        url = f"{self._config.base_url.rstrip('/')}/api/chat"
        payload = self._build_payload(messages, stream=True)

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"Ollama API error {resp.status}: {body}"
                    )
                async for line in resp.content:
                    if not line:
                        continue
                    data = json.loads(line)
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
        except aiohttp.ClientError as exc:
            raise LLMError(f"Ollama connection error: {exc}") from exc

    async def complete_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
    ) -> ChatMessage:
        session = self._get_session()
        url = f"{self._config.base_url.rstrip('/')}/api/chat"
        payload = self._build_payload(messages, tools=tools)

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise LLMError(
                        f"Ollama API error {resp.status}: {body}"
                    )
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise LLMError(f"Ollama connection error: {exc}") from exc

        msg = data.get("message", {})
        content = msg.get("content", "")

        tool_calls_raw = msg.get("tool_calls", [])
        tool_calls: list[ToolCall] | None = None

        if tool_calls_raw:
            tool_calls = []
            for i, tc in enumerate(tool_calls_raw):
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(ToolCall(
                    id=f"call_{i}",
                    name=fn.get("name", ""),
                    arguments=args,
                ))

        # fallback: some models put tool calls as XML in content
        if not tool_calls and content:
            tool_calls = _parse_xml_tool_calls(content)
            if tool_calls:
                content = _strip_xml_tool_calls(content)
                logger.debug(
                    "Parsed %d tool calls from content XML",
                    len(tool_calls),
                )

        return ChatMessage(
            role=Role.ASSISTANT,
            content=content or "",
            tool_calls=tool_calls if tool_calls else None,
        )
