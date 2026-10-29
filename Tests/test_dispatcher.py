"""Tests for dispatcher."""

import pytest

from cqrs_framing import (
    AggregateRoot,
    DomainEvent,
    DomainEventDispatcher,
    EventHub,
)


class Event1(DomainEvent):
    pass


class Event2(DomainEvent):
    pass


class _Aggregate(AggregateRoot):
    def __init__(self):
        super().__init__()
        self._raise(Event1())
        self._raise(Event2())


def test_dispatcher_sync():
    """Test synchronous event dispatching."""
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    results = []

    hub[Event1] += lambda e: results.append("event1")
    hub[Event2] += lambda e: results.append("event2")

    aggregate = _Aggregate()
    dispatcher.dispatch_from(aggregate)

    assert len(results) == 2
    assert "event1" in results
    assert "event2" in results
    assert len(aggregate.pending_events) == 0


@pytest.mark.asyncio
async def test_dispatcher_async():
    """Test asynchronous event dispatching."""
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    results = []

    async def handler1(e: Event1):
        results.append("event1")

    async def handler2(e: Event2):
        results.append("event2")

    hub[Event1] += handler1
    hub[Event2] += handler2

    aggregate = _Aggregate()
    await dispatcher.dispatch_from_async(aggregate)

    assert len(results) == 2
    assert "event1" in results
    assert "event2" in results
    assert len(aggregate.pending_events) == 0


def test_dispatcher_clears_events():
    """Test that dispatcher clears pending events."""
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)

    aggregate = _Aggregate()
    assert len(aggregate.pending_events) == 2

    dispatcher.dispatch_from(aggregate)

    assert len(aggregate.pending_events) == 0
