"""Tests for broker."""

import asyncio

import pytest

from cqrs_framing import (
    AggregateRoot,
    AsyncHandler,
    Broker,
    CancellationToken,
    CommandResponse,
    DomainEvent,
    DomainEventDispatcher,
    EventHub,
    Handler,
    HandlerRegistry,
    Message,
    Pipeline,
    Response,
)


class _Command(Message):
    def __init__(self, value: str):
        self.value = value


class SyncCommandHandler(Handler[_Command, CommandResponse[str]]):
    def execute(self, message: _Command) -> CommandResponse[str]:
        return Response.ok(f"sync: {message.value}")


class AsyncCommandHandler(AsyncHandler[_Command, CommandResponse[str]]):
    async def execute(
        self, message: _Command, cancellation_token: CancellationToken
    ) -> CommandResponse[str]:
        return Response.ok(f"async: {message.value}")


class _Event(DomainEvent):
    pass


class _Aggregate(AggregateRoot):
    def __init__(self):
        super().__init__()
        self._raise(_Event())


class AggregateCommandHandler(AsyncHandler[_Command, _Aggregate]):
    async def execute(
        self, message: _Command, cancellation_token: CancellationToken
    ) -> _Aggregate:
        return _Aggregate()


def test_sync_broker_handle():
    """Test synchronous broker execution."""
    registry = HandlerRegistry()
    registry.register(_Command, SyncCommandHandler)
    broker = Broker(registry)

    result = broker.handle(_Command("test"))

    assert result.success is True
    assert result.data == "sync: test"


@pytest.mark.asyncio
async def test_async_broker_handle():
    """Test asynchronous broker execution."""
    registry = HandlerRegistry()
    registry.register(_Command, AsyncCommandHandler)
    broker = Broker(registry)

    result = await broker.handle_async(_Command("test"))

    assert result.success is True
    assert result.data == "async: test"


def test_broker_handle_none_raises():
    """Test that handling None raises ValueError."""
    registry = HandlerRegistry()
    broker = Broker(registry)

    with pytest.raises(ValueError, match="cannot be None"):
        broker.handle(None)


@pytest.mark.asyncio
async def test_sync_handle_sync_pipeline_in_running_loop_raises():
    """Broker.handle should fail if it would call asyncio.run in
    a loop.
    """
    registry = HandlerRegistry()
    registry.register(_Command, SyncCommandHandler)

    pipeline = Pipeline()

    async def passthrough_middleware(ctx, next):
        return await next(ctx)

    pipeline.use(passthrough_middleware)

    broker = Broker(registry, sync_pipeline=pipeline)

    with pytest.raises(RuntimeError, match="event loop is running"):
        broker.handle(_Command("test"))


@pytest.mark.asyncio
async def test_broker_handle_async_none_raises():
    """Test that async handling None raises ValueError."""
    registry = HandlerRegistry()
    broker = Broker(registry)

    with pytest.raises(ValueError, match="cannot be None"):
        await broker.handle_async(None)


@pytest.mark.asyncio
async def test_broker_with_domain_dispatcher():
    """Test broker dispatching domain events from aggregate."""
    registry = HandlerRegistry()
    registry.register(_Command, AggregateCommandHandler)

    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    broker = Broker(registry, domain_dispatcher=dispatcher)

    events_received = []

    def event_handler(event: _Event):
        events_received.append(event)

    hub[_Event] += event_handler

    result = await broker.handle_async(_Command("test"))

    assert isinstance(result, _Aggregate)
    assert len(events_received) == 1
    assert isinstance(events_received[0], _Event)


@pytest.mark.asyncio
async def test_broker_cancellation():
    """Test broker respecting cancellation token."""

    class SlowHandler(AsyncHandler[_Command, CommandResponse[str]]):
        async def execute(
            self, message: _Command, cancellation_token: CancellationToken
        ) -> CommandResponse[str]:
            cancellation_token.throw_if_cancelled()
            return Response.ok("done")

    registry = HandlerRegistry()
    registry.register(_Command, SlowHandler)
    broker = Broker(registry)

    token = CancellationToken(cancelled=True)

    with pytest.raises(asyncio.CancelledError):
        await broker.handle_async(_Command("test"), token)
