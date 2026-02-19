"""Router and Route — handler registration and dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from telethon import events

from gramwork.types import EventFilter, HandlerFunc


@dataclass(slots=True)
class Route:
    event_type: type
    filter_kwargs: EventFilter
    handler: HandlerFunc
    priority: int = 0


class Router:
    """Collects Route objects; supports decorator API and composition."""

    def __init__(self) -> None:
        self._routes: list[Route] = []

    @property
    def routes(self) -> list[Route]:
        return sorted(self._routes, key=lambda r: r.priority, reverse=True)

    def add_route(
        self,
        event_type: type,
        handler: HandlerFunc,
        *,
        priority: int = 0,
        **filter_kwargs: Any,
    ) -> None:
        self._routes.append(
            Route(
                event_type=event_type,
                filter_kwargs=filter_kwargs,
                handler=handler,
                priority=priority,
            )
        )

    def include_router(self, router: Router) -> None:
        """Merge another router's routes into this one."""
        self._routes.extend(router._routes)

    # ── Decorator API ──

    def on_message(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.add_route(events.NewMessage, func, priority=priority, **kwargs)
            return func
        return decorator

    def on_edited(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.add_route(events.MessageEdited, func, priority=priority, **kwargs)
            return func
        return decorator

    def on_callback(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.add_route(events.CallbackQuery, func, priority=priority, **kwargs)
            return func
        return decorator

    def on(
        self, event_type: type, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        """Generic event decorator."""
        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.add_route(event_type, func, priority=priority, **kwargs)
            return func
        return decorator
