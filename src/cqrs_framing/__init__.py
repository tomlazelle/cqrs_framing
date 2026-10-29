"""CQRS Framing - Python CQRS + Domain Events Framework."""

from __future__ import annotations

from .broker import Broker
from .cancellation import CancellationToken
from .context import AsyncHandlerContext, HandlerContext
from .decorators import handler, set_default_registry
from .dispatcher import DomainEventDispatcher
from .domain import AggregateRoot, DomainEvent
from .events import Event, EventHub
from .handlers import AsyncHandler, Handler
from .messages import Message
from .pipeline import Middleware, Next, Pipeline
from .registry import (
    DuplicateHandlerError,
    HandlerNotRegisteredError,
    HandlerRegistry,
    InvalidHandlerSignatureError,
)
from .responses import CommandResponse, Response

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("cqrs-framing")
except Exception:
    __version__ = "0.0.0"

__all__ = [
    # Core broker
    "Broker",
    # Messages and handlers
    "Message",
    "Handler",
    "AsyncHandler",
    # Registry
    "HandlerRegistry",
    "HandlerNotRegisteredError",
    "DuplicateHandlerError",
    "InvalidHandlerSignatureError",
    # Context
    "HandlerContext",
    "AsyncHandlerContext",
    # Responses
    "CommandResponse",
    "Response",
    # Pipeline
    "Pipeline",
    "Middleware",
    "Next",
    # Domain events
    "DomainEvent",
    "AggregateRoot",
    "DomainEventDispatcher",
    # Event system
    "Event",
    "EventHub",
    # Decorators
    "handler",
    "set_default_registry",
    # Cancellation
    "CancellationToken",
]
