"""Domain event dispatcher."""

from __future__ import annotations

from .domain import AggregateRoot
from .events import EventHub


class DomainEventDispatcher:
    """
    Dispatcher that publishes domain events from aggregates to the event hub.

    Collects pending events from an aggregate, clears them, and publishes
    each one to the event hub.
    """

    def __init__(self, hub: EventHub) -> None:
        """
        Initialize the dispatcher.

        Args:
            hub: The event hub to publish events to
        """
        self._hub = hub

    def dispatch_from(self, aggregate: AggregateRoot) -> None:
        """
        Dispatch all pending events from an aggregate (synchronous).

        Args:
            aggregate: The aggregate root to dispatch events from
        """
        events = aggregate.pending_events
        aggregate.clear_pending_events()
        for evt in events:
            self._hub.publish(evt)

    async def dispatch_from_async(self, aggregate: AggregateRoot) -> None:
        """
        Dispatch all pending events from an aggregate (asynchronous).

        Args:
            aggregate: The aggregate root to dispatch events from
        """
        events = aggregate.pending_events
        aggregate.clear_pending_events()
        for evt in events:
            await self._hub.publish_async(evt)
