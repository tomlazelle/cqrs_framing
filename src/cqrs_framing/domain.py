"""Domain event and aggregate root abstractions."""

from __future__ import annotations


class DomainEvent:
    """Marker base class for domain events."""

    pass


class AggregateRoot:
    """
    Base class for aggregate roots that can raise domain events.

    Aggregates record events internally and expose them for dispatch
    after successful command execution.
    """

    def __init__(self) -> None:
        self._pending_events: list[DomainEvent] = []

    @property
    def pending_events(self) -> list[DomainEvent]:
        """Get a copy of all pending events."""
        return list(self._pending_events)

    def _raise(self, event: DomainEvent) -> None:
        """
        Record a domain event.

        Args:
            event: The domain event to record
        """
        self._pending_events.append(event)

    def clear_pending_events(self) -> None:
        """Clear all pending events."""
        self._pending_events.clear()
