"""Tests for domain events and aggregates."""

from cqrs_framing import AggregateRoot, DomainEvent


class _Event(DomainEvent):
    def __init__(self, value: str):
        self.value = value


class _Aggregate(AggregateRoot):
    def __init__(self):
        super().__init__()

    def do_something(self, value: str):
        self._raise(_Event(value))


def test_aggregate_raises_events():
    """Test that aggregate can raise events."""
    aggregate = _Aggregate()
    aggregate.do_something("test1")
    aggregate.do_something("test2")

    events = aggregate.pending_events
    assert len(events) == 2
    assert events[0].value == "test1"
    assert events[1].value == "test2"


def test_aggregate_clear_events():
    """Test that aggregate can clear pending events."""
    aggregate = _Aggregate()
    aggregate.do_something("test")

    assert len(aggregate.pending_events) == 1

    aggregate.clear_pending_events()

    assert len(aggregate.pending_events) == 0


def test_pending_events_returns_copy():
    """Test that pending_events returns a copy."""
    aggregate = _Aggregate()
    aggregate.do_something("test")

    events1 = aggregate.pending_events
    events2 = aggregate.pending_events

    assert events1 is not events2
    assert len(events1) == len(events2)
