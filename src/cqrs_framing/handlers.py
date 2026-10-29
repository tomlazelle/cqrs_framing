"""Handler protocols for sync and async execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .cancellation import CancellationToken

TRequest = TypeVar("TRequest", contravariant=True)
TResponse = TypeVar("TResponse", covariant=True)


class Handler(ABC, Generic[TRequest, TResponse]):
    """Base class for synchronous message handlers."""

    @abstractmethod
    def execute(self, message: TRequest) -> TResponse:
        """Execute the handler with the given message."""
        ...


class AsyncHandler(ABC, Generic[TRequest, TResponse]):
    """Base class for asynchronous message handlers."""

    @abstractmethod
    async def execute(
        self, message: TRequest, cancellation_token: CancellationToken
    ) -> TResponse:
        """Execute the handler asynchronously with the given message
        and cancellation token.
        """
        ...
