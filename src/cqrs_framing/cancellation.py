"""Cancellation token for async operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class CancellationToken:
    """Token used to signal cancellation of async operations."""

    cancelled: bool = False

    def throw_if_cancelled(self) -> None:
        """Raise CancelledError if cancellation has been requested."""
        if self.cancelled:
            raise asyncio.CancelledError()
