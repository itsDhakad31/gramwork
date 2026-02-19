"""Plugin protocol."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from gramwork.routing import Router


@runtime_checkable
class Plugin(Protocol):
    """Protocol for gramwork plugins."""

    @property
    def name(self) -> str:
        ...

    @property
    def router(self) -> Router:
        ...

    def configure(self, config: dict[str, Any]) -> None:
        """Called with the plugin's config section before startup."""
        ...

    async def on_startup(self) -> None:
        """Called after the agent connects."""
        ...

    async def on_shutdown(self) -> None:
        """Called before the agent disconnects."""
        ...
