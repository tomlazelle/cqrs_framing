"""Delegate-style event system."""

from __future__ import annotations

import asyncio
import inspect
import weakref
from collections.abc import Awaitable, Callable
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
)

T = TypeVar("T")
Handler = Callable[[T], Any] | Callable[[T], Awaitable[Any]]
StoredHandler = Handler[T] | weakref.WeakMethod[Callable[[T], Any]]


class Event(Generic[T]):
    """
    Delegate-style event that supports += / -= subscription
    syntax.

    Handlers can be synchronous or asynchronous. Weak references
    are used for bound instance methods to avoid memory leaks.
    """

    def __init__(self, *, fail_fast: bool = True) -> None:
        """
        Initialize an event.

        Args:
            fail_fast: If True, exceptions in handlers stop event propagation.
                      If False, exceptions are swallowed and should be logged.
        """
        self._handlers: list[StoredHandler[T]] = []
        self._fail_fast = fail_fast

    def __iadd__(self, handler: Handler[T]) -> Event[T]:
        """
        Subscribe a handler to this event (+= operator).

        Args:
            handler: The handler function to subscribe

        Returns:
            Self for fluent chaining
        """
        if inspect.ismethod(handler) and getattr(handler, "__self__", None) is not None:
            # Bound instance method: keep weak ref to avoid
            # retaining the instance.
            self._handlers.append(weakref.WeakMethod(cast(Callable[[T], Any], handler)))
        else:
            # Function / lambda / staticmethod
            self._handlers.append(handler)
        return self

    def __isub__(self, handler: Handler[T]) -> Event[T]:
        """
        Unsubscribe a handler from this event (-= operator).

        Args:
            handler: The handler function to unsubscribe

        Returns:
            Self for fluent chaining
        """
        for i, h in enumerate(self._handlers):
            fn = h() if isinstance(h, weakref.WeakMethod) else h
            if fn is handler:
                del self._handlers[i]
                break
        return self

    def fire(self, payload: T) -> None:
        """
        Fire the event with fire-and-forget semantics.

        Async handlers are scheduled as tasks but not awaited.

        Args:
            payload: The event data to pass to handlers
        """
        dead: list[int] = []

        try:
            running_loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        for i, h in enumerate(self._handlers):
            fn = h() if isinstance(h, weakref.WeakMethod) else h
            if fn is None:
                dead.append(i)
                continue

            try:
                result = cast(Handler[T], fn)(payload)
                if inspect.isawaitable(result):
                    if running_loop is None:
                        if inspect.iscoroutine(result):
                            result.close()
                        raise RuntimeError(
                            "Event.fire() encountered an async "
                            "handler but no running event loop. Use "
                            "await Event.fire_async(...) / "
                            "EventHub.publish_async(...) or call from "
                            "an async context."
                        )
                    asyncio.ensure_future(cast(Awaitable[Any], result))
            except Exception:
                if self._fail_fast:
                    raise
                # Otherwise swallow/log. Logging strategy is an
                # integration concern.

        for i in reversed(dead):
            del self._handlers[i]

    async def fire_async(self, payload: T) -> None:
        """
        Fire the event with deterministic async semantics.

        All async handlers are awaited before returning.

        Args:
            payload: The event data to pass to handlers
        """
        dead: list[int] = []
        awaitables: list[Awaitable[Any]] = []

        for i, h in enumerate(self._handlers):
            fn = h() if isinstance(h, weakref.WeakMethod) else h
            if fn is None:
                dead.append(i)
                continue

            try:
                result = cast(Handler[T], fn)(payload)
                if inspect.isawaitable(result):
                    awaitables.append(cast(Awaitable[Any], result))
            except Exception:
                if self._fail_fast:
                    raise

        for i in reversed(dead):
            del self._handlers[i]

        if awaitables:
            await asyncio.gather(*awaitables)


class EventHub:
    """
    Central hub for managing typed event channels.

    Supports dictionary-style access: hub[EventType] returns an
    Event[EventType].
    """

    def __init__(self, *, fail_fast: bool = True) -> None:
        """
        Initialize an event hub.

        Args:
            fail_fast: Default fail_fast setting for created event channels
        """
        self._events: dict[type[Any], Event[Any]] = {}
        self._fail_fast = fail_fast

    def channel(self, event_type: type[T]) -> Event[T]:
        """
        Get or create an event channel for the given type.

        Args:
            event_type: The type of event

        Returns:
            The event channel for this type
        """
        ev = self._events.get(event_type)
        if ev is None:
            ev = Event[T](fail_fast=self._fail_fast)
            self._events[event_type] = cast(Event[Any], ev)
        return cast(Event[T], ev)

    def __getitem__(self, event_type: type[T]) -> Event[T]:
        """Get or create an event channel (dict-style access)."""
        return self.channel(event_type)

    def __setitem__(self, event_type: type[T], ev: Event[T]) -> None:
        """
        Set an event channel (required for Python augmented assignment).

        Python performs: tmp = hub[T]; tmp = tmp.__iadd__(...); hub[T] = tmp
        """
        self._events[event_type] = cast(Event[Any], ev)

    def publish(self, evt: Any) -> None:
        """
        Publish an event to its channel (fire-and-forget).

        Args:
            evt: The event instance to publish
        """
        channel = self._events.get(type(evt))
        if channel is not None:
            channel.fire(evt)

    async def publish_async(self, evt: Any) -> None:
        """
        Publish an event to its channel (async, awaits all handlers).

        Args:
            evt: The event instance to publish
        """
        channel = self._events.get(type(evt))
        if channel is not None:
            await channel.fire_async(evt)
