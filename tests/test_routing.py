"""Tests for routing."""

from telethon import events

from gramwork.routing import Router


def test_add_route():
    router = Router()

    @router.on_message(pattern=r"/test")
    async def handler(ctx):
        pass

    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.event_type is events.NewMessage
    assert route.filter_kwargs == {"pattern": r"/test"}


def test_priority_sorting():
    router = Router()

    @router.on_message(priority=1)
    async def low(ctx):
        pass

    @router.on_message(priority=10)
    async def high(ctx):
        pass

    routes = router.routes
    assert routes[0].priority == 10
    assert routes[1].priority == 1


def test_include_router():
    main = Router()
    sub = Router()

    @main.on_message(pattern=r"/a")
    async def a(ctx):
        pass

    @sub.on_message(pattern=r"/b")
    async def b(ctx):
        pass

    main.include_router(sub)
    assert len(main.routes) == 2


def test_on_edited():
    router = Router()

    @router.on_edited()
    async def handler(ctx):
        pass

    assert router.routes[0].event_type is events.MessageEdited


def test_on_callback():
    router = Router()

    @router.on_callback()
    async def handler(ctx):
        pass

    assert router.routes[0].event_type is events.CallbackQuery


def test_generic_on():
    router = Router()

    @router.on(events.ChatAction)
    async def handler(ctx):
        pass

    assert router.routes[0].event_type is events.ChatAction
