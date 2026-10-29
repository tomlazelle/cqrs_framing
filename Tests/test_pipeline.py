"""Tests for pipeline middleware."""

import pytest

from cqrs_framing import AsyncHandlerContext, Message, Pipeline


class _Request(Message):
    def __init__(self, value: str):
        self.value = value


@pytest.mark.asyncio
async def test_pipeline_empty():
    """Test pipeline with no middleware."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c: AsyncHandlerContext[_Request, str]) -> str:
        return f"result: {c.request.value}"

    result = await pipeline.run(ctx, terminal)

    assert result == "result: test"


@pytest.mark.asyncio
async def test_pipeline_single_middleware():
    """Test pipeline with single middleware."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()
    calls = []

    async def middleware(
        ctx: AsyncHandlerContext[_Request, str],
        next,
    ):
        calls.append("before")
        result = await next(ctx)
        calls.append("after")
        return result

    pipeline.use(middleware)
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c: AsyncHandlerContext[_Request, str]) -> str:
        calls.append("terminal")
        return "result"

    result = await pipeline.run(ctx, terminal)

    assert result == "result"
    assert calls == ["before", "terminal", "after"]


@pytest.mark.asyncio
async def test_pipeline_multiple_middleware():
    """Test pipeline with multiple middleware."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()
    calls = []

    async def middleware1(ctx, next):
        calls.append("m1-before")
        result = await next(ctx)
        calls.append("m1-after")
        return result

    async def middleware2(ctx, next):
        calls.append("m2-before")
        result = await next(ctx)
        calls.append("m2-after")
        return result

    pipeline.use(middleware1).use(middleware2)
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c):
        calls.append("terminal")
        return "result"

    await pipeline.run(ctx, terminal)

    assert calls == [
        "m1-before",
        "m2-before",
        "terminal",
        "m2-after",
        "m1-after",
    ]


@pytest.mark.asyncio
async def test_pipeline_short_circuit():
    """Test middleware can short-circuit the pipeline."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()

    async def short_circuit_middleware(ctx, next):
        ctx.should_continue = False
        ctx.response = "short-circuited"
        return "short-circuited"

    pipeline.use(short_circuit_middleware)
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c):
        raise AssertionError("Terminal should not be called")

    result = await pipeline.run(ctx, terminal)

    assert result == "short-circuited"
    assert ctx.should_continue is False


@pytest.mark.asyncio
async def test_pipeline_exception_handling():
    """Test pipeline with exception in middleware."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()

    async def failing_middleware(ctx, next):
        raise ValueError("middleware error")

    pipeline.use(failing_middleware)
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c):
        return "result"

    with pytest.raises(ValueError, match="middleware error"):
        await pipeline.run(ctx, terminal)


@pytest.mark.asyncio
async def test_pipeline_context_modification():
    """Test middleware can modify context."""
    pipeline = Pipeline[AsyncHandlerContext[_Request, str]]()

    async def modifier_middleware(ctx, next):
        ctx.items["modified"] = True
        result = await next(ctx)
        return result

    pipeline.use(modifier_middleware)
    ctx = AsyncHandlerContext(request=_Request("test"))

    async def terminal(c):
        assert c.items.get("modified") is True
        return "result"

    await pipeline.run(ctx, terminal)
