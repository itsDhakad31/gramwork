"""Tests for GramWork app class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gramwork.app import GramWork
from gramwork.config import Config
from gramwork.routing import Router


def test_default_construction():
    app = GramWork()
    assert app.config is not None
    assert app.state is not None
    assert app.llm is None


def test_config_object():
    cfg = Config()
    cfg.telegram.api_id = 123
    app = GramWork(config=cfg)
    assert app.config.telegram.api_id == 123


def test_decorator_api():
    app = GramWork()

    @app.on_message(pattern=r"/test")
    async def handler(ctx):
        pass

    assert len(app.router.routes) == 1


def test_include_router():
    app = GramWork()
    sub = Router()

    @sub.on_message(pattern=r"/sub")
    async def handler(ctx):
        pass

    app.include_router(sub)
    assert len(app.router.routes) == 1


def test_register_plugin():
    app = GramWork()

    plugin = MagicMock()
    plugin.name = "test"
    plugin.router = Router()

    @plugin.router.on_message(pattern=r"/plugin")
    async def handler(ctx):
        pass

    app.register_plugin(plugin)
    assert len(app._plugins) == 1
    assert len(app.router.routes) == 1


def test_add_middleware():
    app = GramWork()

    async def mw(ctx, call_next):
        await call_next()

    app.add_middleware(mw)
    assert len(app.middleware_stack._middlewares) == 1
