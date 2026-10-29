# Quick Start Guide

This guide will help you get started with the CQRS Framing framework in just a few minutes.

## Installation

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install the package in editable mode
pip install -e .
```

## Your First Command

Let's create a simple command to create a user:

```python
import asyncio
from dataclasses import dataclass
from cqrs_framing import (
    AsyncHandler,
    Broker,
    CancellationToken,
    CommandResponse,
    HandlerRegistry,
    Message,
    Response,
)

# 1. Define your command
@dataclass
class CreateUser(Message):
    username: str
    email: str

# 2. Define your handler (must inherit from AsyncHandler)
class CreateUserHandler(AsyncHandler[CreateUser, CommandResponse[str]]):
    async def execute(
        self, 
        command: CreateUser, 
        cancellation_token: CancellationToken
    ) -> CommandResponse[str]:
        # Your business logic here
        user_id = f"user-{command.username}"
        print(f"Created user: {command.username}")
        return Response.ok(user_id)

# 3. Setup and execute
async def main():
    registry = HandlerRegistry()
    broker = Broker(registry)
    
    # Register the handler type (will be auto-instantiated by DI)
    registry.register(CreateUser, CreateUserHandler)
    
    # Execute the command
    result = await broker.handle_async(
        CreateUser(username="john", email="john@example.com")
    )
    
    print(f"Success: {result.success}")
    print(f"User ID: {result.data}")

asyncio.run(main())
```

## Handlers with Dependencies

The framework uses dependency injection powered by `di-done-right`:

```python
# 1. Define a service
class UserRepository:
    def save(self, username: str, email: str) -> str:
        user_id = f"user-{username}"
        print(f"Saving user to database: {username}")
        return user_id

# 2. Handler with dependency (must inherit from AsyncHandler)
class CreateUserHandler(AsyncHandler[CreateUser, CommandResponse[str]]):
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    async def execute(
        self, 
        command: CreateUser, 
        cancellation_token: CancellationToken
    ) -> CommandResponse[str]:
        # Use the injected dependency
        user_id = self.repository.save(command.username, command.email)
        return Response.ok(user_id)

# 3. Register service and handler
async def main():
    registry = HandlerRegistry()
    broker = Broker(registry)
    
    # Register service in DI container
    registry.container.register_instance(UserRepository, UserRepository())
    
    # Register handler type (repository will be auto-injected)
    registry.register(CreateUser, CreateUserHandler)
    
    result = await broker.handle_async(
        CreateUser(username="john", email="john@example.com")
    )
    print(f"User ID: {result.data}")

asyncio.run(main())
```

Let's enhance our example with domain events:

```python
from cqrs_framing import (
    AggregateRoot,
    DomainEvent,
    DomainEventDispatcher,
    EventHub,
)

# 1. Define your event
@dataclass
class UserCreated(DomainEvent):
    user_id: str
    username: str
    email: str

# 2. Create an aggregate that raises events
class User(AggregateRoot):
    def __init__(self, username: str, email: str):
        super().__init__()
        self.user_id = f"user-{username}"
        self.username = username
        self.email = email
        # Raise domain event
        self._raise(UserCreated(
            user_id=self.user_id,
            username=username,
            email=email
        ))

# 3. Update handler to return aggregate (must inherit from AsyncHandler)
class CreateUserHandler(AsyncHandler[CreateUser, User]):
    async def execute(
        self, 
        command: CreateUser, 
        cancellation_token: CancellationToken
    ) -> User:
        return User(command.username, command.email)

# 4. Setup event handlers
async def main():
    registry = HandlerRegistry()
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    broker = Broker(registry, domain_dispatcher=dispatcher)
    
    # Subscribe to events
    def send_welcome_email(event: UserCreated):
        print(f"Sending welcome email to {event.email}")
    
    hub[UserCreated] += send_welcome_email
    
    # Register and execute
    registry.register(CreateUser, CreateUserHandler)
    user = await broker.handle_async(
        CreateUser(username="john", email="john@example.com")
    )
    
    print(f"User created: {user.user_id}")

asyncio.run(main())
```

## Adding Middleware

Add logging and timing middleware:

```python
from cqrs_framing import Pipeline, AsyncHandlerContext
import time

# Define middleware
async def logging_middleware(ctx: AsyncHandlerContext, next):
    print(f"→ Executing: {ctx.request.__class__.__name__}")
    result = await next(ctx)
    print(f"← Completed: success={ctx.success}")
    return result

async def timing_middleware(ctx: AsyncHandlerContext, next):
    start = time.time()
    result = await next(ctx)
    elapsed = (time.time() - start) * 1000
    print(f"⏱ Took {elapsed:.2f}ms")
    return result

# Setup pipeline
pipeline = Pipeline()
pipeline.use(logging_middleware).use(timing_middleware)

broker = Broker(registry, async_pipeline=pipeline)
```

## Async and sync semantics

- If you subscribe async event handlers, prefer `await hub.publish_async(evt)` (or `await event.fire_async(evt)`) so handlers are awaited.
- `hub.publish(evt)` / `event.fire(evt)` are fire-and-forget and require a running event loop to schedule async handlers.
- If you use `Broker.handle(...)` with a `sync_pipeline`, call it from a non-async context (it cannot run inside an already-running event loop).

## Running the Examples

```bash
# Basic usage
python examples/basic_usage.py

# Domain events
python examples/domain_events.py

# Middleware pipeline
python examples/middleware_pipeline.py
```

## Running Tests

```bash
# Run all tests
pytest Tests/

# Run with verbose output
pytest Tests/ -v

# Run specific test file
pytest Tests/test_broker.py -v

# Run with coverage
pytest Tests/ --cov=cqrs_framing
```

## Next Steps

- Explore the [examples/](examples/) folder for more detailed examples
- Read the [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for architecture details
- Check out the full [specification](python_cqrs_domain_events_framework_specification.md)

## Common Patterns

### Command with Validation

```python
async def validation_middleware(ctx, next):
    if isinstance(ctx.request, CreateUser):
        if not ctx.request.email:
            ctx.should_continue = False
            ctx.response = Response.failed("Email is required")
            return ctx.response
    return await next(ctx)
```

### Query Pattern

```python
@dataclass
class GetUser(Message):
    user_id: str

class GetUserHandler:
    async def execute(self, query: GetUser, cancellation_token):
        # Fetch from database
        user = await db.get_user(query.user_id)
        if user:
            return Response.ok(user)
        return Response.failed("User not found")
```

### Event Subscription

```python
# Subscribe multiple handlers to same event
hub[UserCreated] += send_email
hub[UserCreated] += log_audit
hub[UserCreated] += update_analytics

# Unsubscribe
hub[UserCreated] -= send_email
```

Happy coding! 🚀
