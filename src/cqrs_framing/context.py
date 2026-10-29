"""Context objects for handler execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .cancellation import CancellationToken

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


@dataclass
class HandlerContext(Generic[TRequest, TResponse]):
    """Context for synchronous handler execution."""

    request: TRequest
    response: TResponse | None = None
    success: bool = False
    exception: Exception | None = None
    error_message: str | None = None
    should_continue: bool = True
    items: dict[str, Any] = field(default_factory=dict)


@dataclass
class AsyncHandlerContext(Generic[TRequest, TResponse]):
    """Context for asynchronous handler execution."""

    request: TRequest
    cancellation_token: CancellationToken | None = None
    response: TResponse | None = None
    success: bool = False
    exception: Exception | None = None
    error_message: str | None = None
    should_continue: bool = True
    items: dict[str, Any] = field(default_factory=dict)
