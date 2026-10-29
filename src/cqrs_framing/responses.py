"""Command response types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CommandResponse(Generic[T]):
    """Response wrapper for command execution."""

    success: bool
    data: T | None = None
    message: str | None = None
    exception: Exception | None = None

    @property
    def raw_data(self) -> T | None:
        """Get the raw data from the response."""
        return self.data


class Response:
    """Factory for creating command responses."""

    @staticmethod
    def ok(data: T | None = None) -> CommandResponse[T]:
        """Create a successful response."""
        return CommandResponse(success=True, data=data)

    @staticmethod
    def failed(
        message: str | list[str], exception: Exception | None = None
    ) -> CommandResponse[Any]:
        """Create a failed response."""
        if isinstance(message, list):
            message = " ".join(message)
        return CommandResponse(success=False, message=message, exception=exception)
