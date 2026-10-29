"""Tests for cancellation token."""

import asyncio

import pytest

from cqrs_framing import CancellationToken


def test_cancellation_token_not_cancelled():
    """Test that non-cancelled token doesn't raise."""
    token = CancellationToken()
    token.throw_if_cancelled()  # Should not raise


def test_cancellation_token_cancelled():
    """Test that cancelled token raises."""
    token = CancellationToken(cancelled=True)

    with pytest.raises(asyncio.CancelledError):
        token.throw_if_cancelled()


def test_cancellation_token_default():
    """Test default cancellation token state."""
    token = CancellationToken()
    assert token.cancelled is False
