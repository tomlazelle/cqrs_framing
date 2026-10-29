"""Tests for global and handler-specific pipelines."""

import pytest

from cqrs_framing import (
    AsyncHandler,
    Broker,
    Handler,
    HandlerNotRegisteredError,
    HandlerRegistry,
    Message,
    Pipeline,
    handler,
    set_default_registry,
)


class _Req(Message):
    pass


class _Other(Message):
    pass


def _tracer(calls, name, *, short_circuit=False):
    async def mw(ctx, next):
        calls.append(f"{name}:in")
        if short_circuit:
            ctx.response = name
            ctx.should_continue = False
            return name
        result = await next(ctx)
        calls.append(f"{name}:out")
        return result

    return mw


def _async_handler(calls):
    class H(AsyncHandler[_Req, str]):
        async def execute(self, message, cancellation_token):
            calls.append("handler")
            return "ok"

    return H


def _sync_handler(calls):
    class H(Handler[_Req, str]):
        def execute(self, message):
            calls.append("handler")
            return "ok"

    return H


@pytest.mark.asyncio
async def test_async_global_then_handler_pipeline_order():
    calls = []
    g = Pipeline().use(_tracer(calls, "global"))
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)
    broker = Broker(registry, async_pipeline=g)

    assert await broker.handle_async(_Req()) == "ok"
    assert calls == [
        "global:in",
        "handler_mw:in",
        "handler",
        "handler_mw:out",
        "global:out",
    ]


@pytest.mark.asyncio
async def test_async_handler_pipeline_only():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)

    assert await Broker(registry).handle_async(_Req()) == "ok"
    assert calls == ["handler_mw:in", "handler", "handler_mw:out"]


@pytest.mark.asyncio
async def test_async_pipeline_does_not_leak_to_other_requests():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw"))

    class OtherHandler(AsyncHandler[_Other, str]):
        async def execute(self, message, cancellation_token):
            return "other"

    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)
    registry.register(_Other, OtherHandler)

    assert await Broker(registry).handle_async(_Other()) == "other"
    assert calls == []


@pytest.mark.asyncio
async def test_async_handler_pipeline_short_circuit():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw", short_circuit=True))
    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)

    assert await Broker(registry).handle_async(_Req()) == "handler_mw"
    assert "handler" not in calls


@pytest.mark.asyncio
async def test_async_global_short_circuit_skips_handler_pipeline():
    calls = []
    g = Pipeline().use(_tracer(calls, "global", short_circuit=True))
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)

    assert await Broker(registry, async_pipeline=g).handle_async(_Req()) == "global"
    assert calls == ["global:in"]


@pytest.mark.asyncio
async def test_async_should_continue_false_skips_handler_pipeline():
    calls = []

    async def stop(ctx, next):
        ctx.should_continue = False
        return await next(ctx)

    g = Pipeline().use(stop)
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _async_handler(calls), pipeline=h)

    await Broker(registry, async_pipeline=g).handle_async(_Req())
    assert calls == []


@pytest.mark.asyncio
async def test_async_exception_propagates_through_both_pipelines():
    seen = []

    async def catcher(ctx, next):
        try:
            return await next(ctx)
        except ValueError:
            seen.append((ctx.success, ctx.error_message))
            raise

    class Boom(AsyncHandler[_Req, str]):
        async def execute(self, message, cancellation_token):
            raise ValueError("boom")

    registry = HandlerRegistry()
    registry.register(_Req, Boom, pipeline=Pipeline().use(catcher))
    broker = Broker(registry, async_pipeline=Pipeline().use(catcher))

    with pytest.raises(ValueError):
        await broker.handle_async(_Req())
    assert seen == [(False, "boom"), (False, "boom")]


def test_sync_global_then_handler_pipeline_order():
    calls = []
    g = Pipeline().use(_tracer(calls, "global"))
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _sync_handler(calls), pipeline=h)
    broker = Broker(registry, sync_pipeline=g)

    assert broker.handle(_Req()) == "ok"
    assert calls == [
        "global:in",
        "handler_mw:in",
        "handler",
        "handler_mw:out",
        "global:out",
    ]


def test_sync_handler_pipeline_only():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _sync_handler(calls), pipeline=h)

    assert Broker(registry).handle(_Req()) == "ok"
    assert calls == ["handler_mw:in", "handler", "handler_mw:out"]


@pytest.mark.asyncio
async def test_sync_handler_pipeline_inside_running_loop_raises():
    h = Pipeline().use(_tracer([], "handler_mw"))
    registry = HandlerRegistry()
    registry.register(_Req, _sync_handler([]), pipeline=h)

    with pytest.raises(RuntimeError, match="event loop"):
        Broker(registry).handle(_Req())


def test_register_instance_with_pipeline():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    registry.register_instance(_Req, _sync_handler(calls)(), pipeline=h)

    assert Broker(registry).handle(_Req()) == "ok"
    assert calls == ["handler_mw:in", "handler", "handler_mw:out"]


@pytest.mark.asyncio
async def test_decorator_with_pipeline():
    calls = []
    h = Pipeline().use(_tracer(calls, "handler_mw"))
    registry = HandlerRegistry()
    set_default_registry(registry)

    @handler(_Req, pipeline=h)
    class H(AsyncHandler[_Req, str]):
        async def execute(self, message, cancellation_token):
            calls.append("handler")
            return "ok"

    assert await Broker(registry).handle_async(_Req()) == "ok"
    assert calls == ["handler_mw:in", "handler", "handler_mw:out"]


def test_pipeline_lookup_returns_none_when_absent():
    registry = HandlerRegistry()
    registry.register(_Req, _sync_handler([]))
    assert registry.sync_pipeline_for(_Req) is None
    assert registry.async_pipeline_for(_Req) is None


def test_unregistered_request_still_raises_with_global_pipeline():
    broker = Broker(HandlerRegistry(), sync_pipeline=Pipeline())
    with pytest.raises(HandlerNotRegisteredError):
        broker.handle(_Req())
