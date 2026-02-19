"""Middleware protocol and stack — Starlette-inspired pipeline."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gramwork.context import EventContext
from gramwork.types import NextFunc


@runtime_checkable
class Middleware(Protocol):
    async def __call__(self, ctx: EventContext, call_next: NextFunc) -> None:
        ...


class MiddlewareStack:
    """Builds a chain of middleware wrapping a final handler dispatch."""

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> None:
        self._middlewares.append(middleware)

    async def execute(self, ctx: EventContext, handler: NextFunc) -> None:
        """Run the full middleware chain, ending with the handler."""

        async def _build_chain(index: int) -> None:
            if index >= len(self._middlewares):
                await handler()
                return

            mw = self._middlewares[index]

            async def call_next() -> None:
                await _build_chain(index + 1)

            await mw(ctx, call_next)

        await _build_chain(0)
