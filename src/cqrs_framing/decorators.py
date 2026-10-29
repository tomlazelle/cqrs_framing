"""Decorator-based handler registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .pipeline import Pipeline
from .registry import HandlerRegistry

_registry_singleton: HandlerRegistry | None = None


def set_default_registry(registry: HandlerRegistry) -> None:
    """
    Set the default registry for decorator-based registration.

    Args:
        registry: The registry to use as the default
    """
    global _registry_singleton
    _registry_singleton = registry


def handler(
    request_type: type[Any], pipeline: Pipeline[Any] | None = None
) -> Callable[[type[Any]], type[Any]]:
    """
    Decorator to register a handler class for a request type.

    Usage:
        @handler(CreateUser)
        class CreateUserHandler:
            async def execute(self, message: CreateUser, cancellation_token)
            -> CommandResponse:
                ...

    Args:
        request_type: The request type this handler processes
        pipeline: Optional middleware pipeline wrapping only this handler

    Returns:
        A decorator function

    Raises:
        RuntimeError: If default registry is not set
    """

    def decorator(cls: type[Any]) -> type[Any]:
        if _registry_singleton is None:
            raise RuntimeError(
                "Default registry not set. Call set_default_registry(...)"
                " during bootstrap."
            )
        _registry_singleton.register(request_type, cls, pipeline)
        return cls

    return decorator
