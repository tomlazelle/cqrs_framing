"""Example: Using middleware pipeline."""

import asyncio
import time
from dataclasses import dataclass

from cqrs_framing import (
    AsyncHandler,
    AsyncHandlerContext,
    Broker,
    CommandResponse,
    HandlerRegistry,
    Message,
    Pipeline,
    Response,
)


# Command
@dataclass
class ProcessPayment(Message):
    """Command to process a payment."""

    payment_id: str
    amount: float


# Handler
class ProcessPaymentHandler(AsyncHandler[ProcessPayment, CommandResponse[str]]):
    """Handler for processing payments."""

    async def execute(
        self, command: ProcessPayment, cancellation_token
    ) -> CommandResponse[str]:
        """Execute the payment processing."""
        # Simulate payment processing
        await asyncio.sleep(0.1)
        print(f"   💳 Processing payment ${command.amount:.2f}")
        return Response.ok(f"Payment {command.payment_id} processed")


# Middleware
async def logging_middleware(ctx: AsyncHandlerContext, next):
    """Log request and response."""
    print(f"→ Request: {ctx.request.__class__.__name__}")
    result = await next(ctx)
    print(f"← Response: success={ctx.success}")
    return result


async def timing_middleware(ctx: AsyncHandlerContext, next):
    """Measure execution time."""
    start = time.time()
    result = await next(ctx)
    elapsed = (time.time() - start) * 1000
    print(f"⏱  Execution time: {elapsed:.2f}ms")
    return result


async def validation_middleware(ctx: AsyncHandlerContext, next):
    """Validate request before processing."""
    print("✓ Validating request...")

    # Example validation
    if isinstance(ctx.request, ProcessPayment):
        if ctx.request.amount <= 0:
            print("✗ Validation failed: Invalid amount")
            ctx.should_continue = False
            ctx.response = Response.failed("Amount must be greater than 0")
            return ctx.response

    result = await next(ctx)
    return result


async def exception_handling_middleware(ctx: AsyncHandlerContext, next):
    """Handle exceptions gracefully."""
    try:
        result = await next(ctx)
        return result
    except Exception as e:
        print(f"✗ Exception caught: {e}")
        ctx.success = False
        ctx.exception = e
        ctx.response = Response.failed(str(e), exception=e)
        return ctx.response


async def transaction_middleware(ctx: AsyncHandlerContext, next):
    """Simulate transaction management."""
    print("  ▶ BEGIN TRANSACTION")
    try:
        result = await next(ctx)
        if ctx.success:
            print("  ✓ COMMIT TRANSACTION")
        else:
            print("  ✗ ROLLBACK TRANSACTION")
        return result
    except Exception:
        print("  ✗ ROLLBACK TRANSACTION")
        raise


async def main():
    """Run the example."""
    print("=== Pipeline Middleware Example ===\n")

    # Global pipeline: runs for every request handled by the broker
    global_pipeline = Pipeline[AsyncHandlerContext]()
    global_pipeline.use(logging_middleware)
    global_pipeline.use(timing_middleware)
    global_pipeline.use(exception_handling_middleware)

    # Handler pipeline: runs only for ProcessPayment, inside the global one
    payment_pipeline = Pipeline[AsyncHandlerContext]()
    payment_pipeline.use(validation_middleware)
    payment_pipeline.use(transaction_middleware)

    registry = HandlerRegistry()
    registry.register(ProcessPayment, ProcessPaymentHandler, pipeline=payment_pipeline)

    broker = Broker(registry, async_pipeline=global_pipeline)

    # Example 1: Valid payment
    print("Example 1: Valid payment\n")
    result1 = await broker.handle_async(
        ProcessPayment(payment_id="PAY-001", amount=99.99)
    )
    print(f"\nResult: {result1.data}\n")
    print("-" * 50 + "\n")

    # Example 2: Invalid payment (validation fails)
    print("Example 2: Invalid payment (validation fails)\n")
    result2 = await broker.handle_async(
        ProcessPayment(payment_id="PAY-002", amount=-50.00)
    )
    print(f"\nResult: {result2.message}\n")
    print("-" * 50 + "\n")

    # Example 3: Global pipeline only (handler registered without a pipeline)
    print("Example 3: Global pipeline only\n")
    plain_registry = HandlerRegistry()
    plain_registry.register(ProcessPayment, ProcessPaymentHandler)

    plain_broker = Broker(plain_registry, async_pipeline=global_pipeline)
    result3 = await plain_broker.handle_async(
        ProcessPayment(payment_id="PAY-003", amount=49.99)
    )
    print(f"\nResult: {result3.data}\n")


if __name__ == "__main__":
    asyncio.run(main())
