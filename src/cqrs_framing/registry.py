"""Handler registry using DI container for request type to
handler mapping.
"""

from __future__ import annotations

import inspect
from typing import Any

from di_container import DIContainer  # type: ignore[import-untyped]

from .pipeline import Pipeline


class HandlerNotRegisteredError(RuntimeError):
    """Raised when no handler is registered for a request type."""

    pass


class DuplicateHandlerError(RuntimeError):
    """Raised when attempting to register a duplicate handler."""

    pass


class InvalidHandlerSignatureError(TypeError):
    """Raised when a handler's execute method has an invalid signature."""

    pass


def _validate_handler_signature(handler_type: type[Any], execute_method: Any) -> None:
    """
    Validate that a handler's execute method has the correct signature.

    Args:
        handler_type: The handler class being validated
        execute_method: The execute method to validate

    Raises:
        InvalidHandlerSignatureError: If the signature is invalid
    """
    # Import here to avoid circular dependency
    from .handlers import AsyncHandler, Handler

    # Check if handler inherits from base classes
    is_async_handler = issubclass(handler_type, AsyncHandler)
    is_sync_handler = issubclass(handler_type, Handler)

    if not is_async_handler and not is_sync_handler:
        raise InvalidHandlerSignatureError(
            f"Handler {handler_type.__name__} must inherit from "
            f"either cqrs_framing.Handler or "
            f"cqrs_framing.AsyncHandler. Import and inherit from "
            f"the appropriate base class."
        )

    sig = inspect.signature(execute_method)
    params = list(sig.parameters.values())

    # Remove 'self' or 'cls' if present
    if params and params[0].name in ("self", "cls"):
        params = params[1:]

    is_async = inspect.iscoroutinefunction(execute_method)

    if is_async:
        # Async handler must have exactly 2 parameters:
        # (message, cancellation_token)
        if len(params) < 2:
            raise InvalidHandlerSignatureError(
                f"Async handler {handler_type.__name__}.execute() "
                f"must have signature: execute(self, message: "
                f"TRequest, cancellation_token: CancellationToken) "
                f"-> TResponse. Found {len(params)} parameter(s) "
                f"after 'self': {[p.name for p in params]}"
            )
        # Allow extra optional parameters, but first 2 must be
        # present
        if len(params) > 2:
            # Check if extra params have defaults
            extra_params = params[2:]
            if not all(p.default != inspect.Parameter.empty for p in extra_params):
                raise InvalidHandlerSignatureError(
                    f"Async handler {handler_type.__name__}.execute() "
                    f"has extra required parameters. Only (message, "
                    f"cancellation_token) are required. Extra params "
                    f"must have defaults."
                )
    else:
        # Sync handler must have exactly 1 parameter: (message)
        if len(params) < 1:
            raise InvalidHandlerSignatureError(
                f"Sync handler {handler_type.__name__}.execute() "
                f"must have signature: execute(self, message: "
                f"TRequest) -> TResponse. Found {len(params)} "
                f"parameter(s) after 'self'."
            )
        # Allow extra optional parameters
        if len(params) > 1:
            extra_params = params[1:]
            if not all(p.default != inspect.Parameter.empty for p in extra_params):
                raise InvalidHandlerSignatureError(
                    f"Sync handler {handler_type.__name__}.execute() "
                    f"has extra required parameters. Only (message) "
                    f"is required. Extra params must have defaults."
                )


class HandlerRegistry:
    """Registry that maps request types to handlers using DI
    container.
    """

    def __init__(self, container: DIContainer | None = None) -> None:
        """
        Initialize the registry with an optional DI container.

        Args:
            container: DI container for resolving handlers. If None, creates a
                new one.
        """
        self._container = container if container is not None else DIContainer()
        self._sync: dict[type[Any], type[Any]] = {}
        self._async: dict[type[Any], type[Any]] = {}
        self._sync_pipelines: dict[type[Any], Pipeline[Any]] = {}
        self._async_pipelines: dict[type[Any], Pipeline[Any]] = {}

    @property
    def container(self) -> DIContainer:
        """Get the underlying DI container."""
        return self._container

    def register(
        self,
        request_type: type[Any],
        handler_type: type[Any],
        pipeline: Pipeline[Any] | None = None,
    ) -> None:
        """
        Register a handler type for a request type.

        The handler will be resolved from the DI container when
        needed.

        Args:
            request_type: The type of request this handler processes
            handler_type: The handler class (will be resolved with
                dependencies)
            pipeline: Optional middleware pipeline that wraps only this
                handler. Runs inside the broker's global pipeline.

        Raises:
            TypeError: If handler doesn't have an execute method
            InvalidHandlerSignatureError: If execute method signature
                is invalid
            DuplicateHandlerError: If a handler is already registered
                for this request type
        """
        # Check if handler has execute method
        execute = getattr(handler_type, "execute", None)
        if execute is None:
            raise TypeError(
                f"Handler {handler_type.__name__} must provide an "
                f"execute(...) method"
            )

        # Validate the execute method signature
        _validate_handler_signature(handler_type, execute)

        # Register handler type in container if not already registered
        if not self._container.is_registered(handler_type):
            self._container.register(handler_type)

        # Determine if sync or async
        self._map(request_type, handler_type, execute, pipeline)

    def register_instance(
        self,
        request_type: type[Any],
        handler_instance: Any,
        pipeline: Pipeline[Any] | None = None,
    ) -> None:
        """
        Register a pre-instantiated handler instance.

        Use this for handlers that don't need DI or when you want
        full control.

        Args:
            request_type: The type of request this handler processes
            handler_instance: The handler instance
            pipeline: Optional middleware pipeline that wraps only this
                handler. Runs inside the broker's global pipeline.

        Raises:
            TypeError: If handler doesn't have an execute method
            InvalidHandlerSignatureError: If execute method signature
                is invalid
            DuplicateHandlerError: If a handler is already registered
                for this request type
        """
        execute = getattr(handler_instance, "execute", None)
        if execute is None:
            raise TypeError(
                f"Handler {type(handler_instance).__name__} must "
                f"provide an execute(...) method"
            )

        handler_type = type(handler_instance)

        # Validate the execute method signature
        _validate_handler_signature(handler_type, execute)

        # Register as singleton instance in container
        self._container.register_instance(handler_type, handler_instance)

        # Map request to handler type
        self._map(request_type, handler_type, execute, pipeline)

    def _map(
        self,
        request_type: type[Any],
        handler_type: type[Any],
        execute: Any,
        pipeline: Pipeline[Any] | None,
    ) -> None:
        """Record the request -> handler (and optional pipeline) mapping."""
        if inspect.iscoroutinefunction(execute):
            handlers, pipelines, kind = self._async, self._async_pipelines, "Async"
        else:
            handlers, pipelines, kind = self._sync, self._sync_pipelines, "Sync"
        if request_type in handlers:
            raise DuplicateHandlerError(
                f"{kind} handler already registered for {request_type.__name__}"
            )
        handlers[request_type] = handler_type
        if pipeline is not None:
            pipelines[request_type] = pipeline

    def sync_pipeline_for(self, request_type: type[Any]) -> Pipeline[Any] | None:
        """Get the handler-specific sync pipeline, or None if there is none."""
        return self._sync_pipelines.get(request_type)

    def async_pipeline_for(self, request_type: type[Any]) -> Pipeline[Any] | None:
        """Get the handler-specific async pipeline, or None if there is none."""
        return self._async_pipelines.get(request_type)

    def resolve_sync(self, request_type: type[Any]) -> Any:
        """
        Resolve a synchronous handler for the given request type.

        Args:
            request_type: The request type to resolve

        Returns:
            The handler instance (resolved from DI container)

        Raises:
            HandlerNotRegisteredError: If no sync handler is registered
        """
        handler_type = self._sync.get(request_type)
        if handler_type is None:
            raise HandlerNotRegisteredError(
                f"No sync handler registered for {request_type.__name__}"
            )
        return self._container.resolve(handler_type)

    def resolve_async(self, request_type: type[Any]) -> Any:
        """
        Resolve an asynchronous handler for the given request type.

        Args:
            request_type: The request type to resolve

        Returns:
            The handler instance (resolved from DI container)

        Raises:
            HandlerNotRegisteredError: If no async handler is registered
        """
        handler_type = self._async.get(request_type)
        if handler_type is None:
            raise HandlerNotRegisteredError(
                f"No async handler registered for {request_type.__name__}"
            )
        return self._container.resolve(handler_type)
