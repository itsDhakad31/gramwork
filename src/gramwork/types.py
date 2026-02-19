"""Type aliases used throughout gramwork."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from gramwork.context import EventContext

HandlerFunc = Callable[["EventContext"], Awaitable[Any]]
NextFunc = Callable[[], Awaitable[None]]
MiddlewareFunc = Callable[["EventContext", NextFunc], Awaitable[None]]
EventFilter = dict[str, Any]
