"""Tool protocol, spec, and registry for the autonomous agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def parameters(self) -> dict[str, Any]: ...

    async def execute(self, **kwargs: Any) -> str: ...


@dataclass(slots=True)
class ToolSpec:
    """Wraps an async callable with JSON Schema metadata."""

    name: str
    description: str
    parameters: dict[str, Any]
    _fn: Callable[..., Awaitable[str]]

    async def execute(self, **kwargs: Any) -> str:
        return await self._fn(**kwargs)

    def to_function_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def get_schemas(self) -> list[dict[str, Any]]:
        return [t.to_function_schema() for t in self._tools.values()]

    @property
    def tools(self) -> dict[str, ToolSpec]:
        return dict(self._tools)

    def __len__(self) -> int:
        return len(self._tools)
