"""Pipeline middleware implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

TContext = TypeVar("TContext")
Next = Callable[[TContext], Awaitable[Any]]
Middleware = Callable[[TContext, Next], Awaitable[Any]]


class Pipeline(Generic[TContext]):
    """
    Pipeline for executing middleware in sequence.

    Middleware are executed in the order they are added, with each
    middleware responsible for calling the next one in the chain.
    """

    def __init__(self) -> None:
        self._middleware: list[Middleware[TContext]] = []

    def use(self, mw: Middleware[TContext]) -> Pipeline[TContext]:
        """
        Add middleware to the pipeline.

        Args:
            mw: The middleware function to add

        Returns:
            Self for fluent chaining
        """
        self._middleware.append(mw)
        return self

    async def run(self, ctx: TContext, terminal: Next[TContext]) -> Any:
        """
        Execute the pipeline with the given context.

        Args:
            ctx: The context to pass through the pipeline
            terminal: The final handler to execute after all middleware

        Returns:
            The result from the terminal handler
        """

        async def invoke(i: int, c: TContext) -> Any:
            if i >= len(self._middleware):
                return await terminal(c)
            return await self._middleware[i](c, lambda cc: invoke(i + 1, cc))

        return await invoke(0, ctx)
