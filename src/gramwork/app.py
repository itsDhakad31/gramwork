"""GramWork — the central application class."""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any, Callable

from telethon import events as telethon_events
from telethon.sessions import StringSession

from gramwork.agent import Agent
from gramwork.config import Config, load_config
from gramwork.context import EventContext
from gramwork.exceptions import StopPropagation
from gramwork.llm.base import LLMProvider
from gramwork.middleware import Middleware, MiddlewareStack
from gramwork.routing import Route, Router
from gramwork.state.base import StateBackend
from gramwork.state.memory import MemoryBackend
from gramwork.tools.base import ToolRegistry
from gramwork.types import HandlerFunc

logger = logging.getLogger("gramwork")


class GramWork:
    """Central application — owns agent, router, middleware, plugins."""

    def __init__(
        self,
        config: Config | None = None,
        config_path: str | None = None,
        *,
        llm: LLMProvider | None = None,
        state: StateBackend | None = None,
        session: StringSession | None = None,
    ) -> None:
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = load_config(config_path)
        else:
            self.config = Config()

        self.router = Router()
        self.middleware_stack = MiddlewareStack()
        self.llm = llm
        self.state: StateBackend = state or MemoryBackend()
        self._agent = Agent(self.config.telegram, session=session)
        self._plugins: list[Any] = []
        self._started = False
        self._tool_registry = ToolRegistry()
        self._brain: Any | None = None

    # ── Decorator API (delegates to router) ──

    def on_message(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        return self.router.on_message(priority=priority, **kwargs)

    def on_edited(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        return self.router.on_edited(priority=priority, **kwargs)

    def on_callback(
        self, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        return self.router.on_callback(priority=priority, **kwargs)

    def on(
        self, event_type: type, *, priority: int = 0, **kwargs: Any
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        return self.router.on(event_type, priority=priority, **kwargs)

    # ── Middleware ──

    def add_middleware(self, middleware: Middleware) -> None:
        self.middleware_stack.add(middleware)

    # ── Plugins ──

    def include_router(self, router: Router) -> None:
        self.router.include_router(router)

    def register_plugin(self, plugin: Any) -> None:
        """Register a plugin instance. Merges its router and stores for lifecycle."""
        self._plugins.append(plugin)
        if hasattr(plugin, "router") and plugin.router is not None:
            self.include_router(plugin.router)

    # ── Internal dispatch ──

    def _build_handler(self, route: Route, event: Any) -> Any:
        """Create an EventContext and dispatch through the middleware stack."""

        async def dispatch() -> None:
            ctx = EventContext(
                event, llm=self.llm, state=self.state, app=self
            )
            try:
                async def run_handler() -> None:
                    await route.handler(ctx)

                await self.middleware_stack.execute(ctx, run_handler)
            except StopPropagation:
                raise
            except Exception:
                logger.exception("Error in handler %s", route.handler.__name__)

        return dispatch

    def _register_handlers(self) -> None:
        """Register all routes as Telethon event handlers."""
        client = self._agent.client
        for route in self.router.routes:
            event_instance = route.event_type(**route.filter_kwargs)

            async def _handler(event: Any, _route: Route = route) -> None:
                ctx = EventContext(
                    event, llm=self.llm, state=self.state, app=self
                )
                try:
                    async def run_handler() -> None:
                        await _route.handler(ctx)

                    await self.middleware_stack.execute(ctx, run_handler)
                except StopPropagation:
                    raise telethon_events.StopPropagation
                except Exception:
                    logger.exception(
                        "Error in handler %s", _route.handler.__name__
                    )

            client.add_event_handler(_handler, event_instance)

    def _setup_autonomous(self) -> None:
        if not self.config.agent.autonomous:
            return
        if self.llm is None:
            logger.warning("Autonomous mode requires an LLM provider — skipping")
            return

        from gramwork.autonomous import AutonomousBrain
        from gramwork.tools.telegram import register_telegram_tools

        register_telegram_tools(
            self._agent.client,
            self._tool_registry,
            allowed=self.config.agent.tools,
        )
        self._brain = AutonomousBrain(
            client=self._agent.client,
            llm=self.llm,
            registry=self._tool_registry,
            config=self.config.agent,
        )
        logger.info(
            "Autonomous brain configured with %d tools", len(self._tool_registry)
        )

    # ── Lifecycle ──

    async def start(self) -> None:
        """Start the agent and all plugins."""
        if self._started:
            return

        # Configure plugins
        for plugin in self._plugins:
            if hasattr(plugin, "configure"):
                plugin_cfg = self.config.plugins.get(
                    getattr(plugin, "name", ""), {}
                )
                await _maybe_await(plugin.configure(plugin_cfg))

        await self._agent.start()
        self._register_handlers()

        self._setup_autonomous()
        if self._brain is not None:
            await self._brain.start()

        # Plugin startup hooks
        for plugin in self._plugins:
            if hasattr(plugin, "on_startup"):
                await _maybe_await(plugin.on_startup())

        self._started = True
        logger.info("GramWork started")

    async def stop(self) -> None:
        """Stop the agent and all plugins."""
        if not self._started:
            return

        if self._brain is not None:
            await self._brain.stop()

        for plugin in self._plugins:
            if hasattr(plugin, "on_shutdown"):
                await _maybe_await(plugin.on_shutdown())

        await self.state.close()
        await self._agent.stop()
        self._started = False
        logger.info("GramWork stopped")

    def run(self) -> None:
        """Blocking entry point with signal handling."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _main() -> None:
            await self.start()
            stop_event = asyncio.Event()

            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)

            await stop_event.wait()
            await self.stop()

        try:
            loop.run_until_complete(_main())
        finally:
            loop.close()


async def _maybe_await(result: Any) -> Any:
    """Await if the result is a coroutine, otherwise return it."""
    if asyncio.iscoroutine(result):
        return await result
    return result
