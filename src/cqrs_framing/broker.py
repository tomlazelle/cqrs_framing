"""Central broker for dispatching commands and queries."""

from __future__ import annotations

from typing import Any

from .cancellation import CancellationToken
from .context import AsyncHandlerContext, HandlerContext
from .dispatcher import DomainEventDispatcher
from .domain import AggregateRoot
from .pipeline import Pipeline
from .registry import HandlerRegistry


class Broker:
    """
    Central broker for dispatching commands and queries to their
    handlers.

    Supports both synchronous and asynchronous execution with
    optional middleware pipelines and domain event dispatching.
    """

    def __init__(
        self,
        registry: HandlerRegistry,
        *,
        sync_pipeline: Pipeline[Any] | None = None,
        async_pipeline: Pipeline[Any] | None = None,
        domain_dispatcher: DomainEventDispatcher | None = None,
    ) -> None:
        """
        Initialize the broker.

        Args:
            registry: Handler registry for resolving handlers
            sync_pipeline: Optional middleware pipeline for sync handlers
            async_pipeline: Optional middleware pipeline for async handlers
            domain_dispatcher: Optional dispatcher for domain events
        """
        self._registry = registry
        self._sync_pipeline = sync_pipeline
        self._async_pipeline = async_pipeline
        self._domain_dispatcher = domain_dispatcher

    def handle(self, request: Any) -> Any:
        """
        Handle a request synchronously.

        Args:
            request: The request/message to handle

        Returns:
            The handler's response

        Raises:
            ValueError: If request is None
            HandlerNotRegisteredError: If no handler is registered
        """
        if request is None:
            raise ValueError("request cannot be None")

        ctx: HandlerContext[Any, Any] = HandlerContext(request=request)

        def invoke_handler(c: HandlerContext[Any, Any]) -> Any:
            handler = self._registry.resolve_sync(type(c.request))
            try:
                result = handler.execute(c.request)
                c.response = result
                c.success = True
                return result
            except Exception as ex:
                c.success = False
                c.exception = ex
                c.error_message = str(ex)
                raise

        async def terminal(c: HandlerContext[Any, Any]) -> Any:
            if not c.should_continue:
                return c.response
            # Look up by the current request type: global middleware may
            # have replaced ctx.request.
            handler_pipeline = self._registry.sync_pipeline_for(type(c.request))
            if handler_pipeline is None:
                return invoke_handler(c)

            async def inner(cc: HandlerContext[Any, Any]) -> Any:
                if not cc.should_continue:
                    return cc.response
                return invoke_handler(cc)

            return await handler_pipeline.run(c, inner)

        if (
            self._sync_pipeline is not None
            or self._registry.sync_pipeline_for(type(request)) is not None
        ):
            import asyncio

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                raise RuntimeError(
                    "Broker.handle() cannot execute a sync pipeline "
                    "while an event loop is running. Use "
                    "Broker.handle_async(...) or call "
                    "Broker.handle(...) from a non-async context."
                )

            if self._sync_pipeline is not None:
                result = asyncio.run(self._sync_pipeline.run(ctx, terminal))
            else:
                result = asyncio.run(terminal(ctx))
        else:
            result = invoke_handler(ctx)

        # Domain events: if the handler returned an AggregateRoot,
        # dispatch its events.
        if self._domain_dispatcher is not None and isinstance(result, AggregateRoot):
            self._domain_dispatcher.dispatch_from(result)

        return result

    async def handle_async(
        self,
        request: Any,
        cancellation_token: CancellationToken | None = None,
    ) -> Any:
        """
        Handle a request asynchronously.

        Args:
            request: The request/message to handle
            cancellation_token: Optional token for cancellation

        Returns:
            The handler's response

        Raises:
            ValueError: If request is None
            HandlerNotRegisteredError: If no handler is registered
            asyncio.CancelledError: If cancellation is requested
        """
        if request is None:
            raise ValueError("request cannot be None")

        if cancellation_token is None:
            cancellation_token = CancellationToken()

        ctx: AsyncHandlerContext[Any, Any] = AsyncHandlerContext(
            request=request,
            cancellation_token=cancellation_token,
        )

        async def invoke_handler(c: AsyncHandlerContext[Any, Any]) -> Any:
            if c.cancellation_token:
                c.cancellation_token.throw_if_cancelled()
            handler = self._registry.resolve_async(type(c.request))
            try:
                result = await handler.execute(c.request, c.cancellation_token)
                c.response = result
                c.success = True
                return result
            except Exception as ex:
                c.success = False
                c.exception = ex
                c.error_message = str(ex)
                raise

        async def terminal(c: AsyncHandlerContext[Any, Any]) -> Any:
            if not c.should_continue:
                return c.response
            # Look up by the current request type: global middleware may
            # have replaced ctx.request.
            handler_pipeline = self._registry.async_pipeline_for(type(c.request))
            if handler_pipeline is None:
                return await invoke_handler(c)

            async def inner(cc: AsyncHandlerContext[Any, Any]) -> Any:
                if not cc.should_continue:
                    return cc.response
                return await invoke_handler(cc)

            return await handler_pipeline.run(c, inner)

        if self._async_pipeline is not None:
            result = await self._async_pipeline.run(ctx, terminal)
        else:
            result = await terminal(ctx)

        if self._domain_dispatcher is not None and isinstance(result, AggregateRoot):
            await self._domain_dispatcher.dispatch_from_async(result)

        return result
