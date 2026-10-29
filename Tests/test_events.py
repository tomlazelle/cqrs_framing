"""Tests for event system."""

import asyncio

import pytest

from cqrs_framing import DomainEvent, Event, EventHub


class _Event(DomainEvent):
    def __init__(self, value: str):
        self.value = value


def test_event_subscribe_and_fire():
    """Test subscribing to and firing an event."""
    event = Event[_Event]()
    results = []

    def handler(e: _Event):
        results.append(e.value)

    event += handler
    event.fire(_Event("test"))

    assert len(results) == 1
    assert results[0] == "test"


def test_event_unsubscribe():
    """Test unsubscribing from an event."""
    event = Event[_Event]()
    results = []

    def handler(e: _Event):
        results.append(e.value)

    event += handler
    event.fire(_Event("test1"))

    event -= handler
    event.fire(_Event("test2"))

    assert len(results) == 1
    assert results[0] == "test1"


def test_event_multiple_handlers():
    """Test multiple handlers on same event."""
    event = Event[_Event]()
    results = []

    def handler1(e: _Event):
        results.append(f"h1: {e.value}")

    def handler2(e: _Event):
        results.append(f"h2: {e.value}")

    event += handler1
    event += handler2
    event.fire(_Event("test"))

    assert len(results) == 2
    assert "h1: test" in results
    assert "h2: test" in results


def test_event_fire_with_async_handler_requires_running_loop():
    """Event.fire should fail if an async handler is used without
    a loop.
    """
    event = Event[_Event]()

    async def async_handler(e: _Event):
        return e.value

    event += async_handler

    with pytest.raises(RuntimeError, match="no running event loop"):
        event.fire(_Event("test"))


@pytest.mark.asyncio
async def test_event_async_handler():
    """Test async event handlers."""
    event = Event[_Event]()
    results = []

    async def async_handler(e: _Event):
        await asyncio.sleep(0.01)
        results.append(e.value)

    event += async_handler
    await event.fire_async(_Event("test"))

    assert len(results) == 1
    assert results[0] == "test"


def test_event_weak_reference_cleanup():
    """Test that bound methods are weakly referenced."""
    event = Event[_Event]()

    class Handler:
        def __init__(self):
            self.called = False

        def handle(self, e: _Event):
            self.called = True

    handler = Handler()
    event += handler.handle
    event.fire(_Event("test"))
    assert handler.called is True

    # Delete handler instance
    del handler

    # Fire again - should not crash
    event.fire(_Event("test2"))


def test_eventhub_channel():
    """Test EventHub channel management."""
    hub = EventHub()
    results = []

    def handler(e: _Event):
        results.append(e.value)

    hub[_Event] += handler
    hub.publish(_Event("test"))

    assert len(results) == 1
    assert results[0] == "test"


@pytest.mark.asyncio
async def test_eventhub_async_publish():
    """Test EventHub async publish."""
    hub = EventHub()
    results = []

    async def handler(e: _Event):
        await asyncio.sleep(0.01)
        results.append(e.value)

    hub[_Event] += handler
    await hub.publish_async(_Event("test"))

    assert len(results) == 1
    assert results[0] == "test"


def test_eventhub_multiple_event_types():
    """Test EventHub with multiple event types."""

    class Event1(DomainEvent):
        pass

    class Event2(DomainEvent):
        pass

    hub = EventHub()
    results = []

    hub[Event1] += lambda e: results.append("event1")
    hub[Event2] += lambda e: results.append("event2")

    hub.publish(Event1())
    hub.publish(Event2())

    assert len(results) == 2
    assert "event1" in results
    assert "event2" in results


def test_event_fail_fast():
    """Test fail_fast behavior."""
    event = Event[_Event](fail_fast=True)

    def bad_handler(e: _Event):
        raise ValueError("handler error")

    event += bad_handler

    with pytest.raises(ValueError, match="handler error"):
        event.fire(_Event("test"))


def test_event_no_fail_fast():
    """Test non-fail-fast behavior swallows exceptions."""
    event = Event[_Event](fail_fast=False)
    results = []

    def bad_handler(e: _Event):
        raise ValueError("handler error")

    def good_handler(e: _Event):
        results.append(e.value)

    event += bad_handler
    event += good_handler

    # Should not raise, good handler should still run
    event.fire(_Event("test"))

    assert len(results) == 1
