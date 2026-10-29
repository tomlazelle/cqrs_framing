# CQRS Framing

A Python framework for CQRS (Command Query Responsibility Segregation) and Domain Events, inspired by .NET's CommandQuery.Framing. Features built-in dependency injection using [di-done-right](https://pypi.org/project/di-done-right/).

## Features

- **CQRS Pattern**: Separate command and query handlers with type-based routing
- **Built-in Dependency Injection**: Uses di-done-right for automatic dependency resolution
- **Sync & Async Support**: Both synchronous and asynchronous handler execution
- **Pipeline Middleware**: Cross-cutting concerns via middleware pattern
- **Domain Events**: First-class domain event support with aggregate roots
- **Delegate-Style Events**: Subscribe to events using `+= / -=` syntax
- **Framework Agnostic**: No dependency on FastAPI or other web frameworks
- **Type Safe**: Full type hints and `py.typed` marker

## Installation

```bash
pip install cqrs-framing
```

## Quick Start

### Handler Contract

All handlers **must** inherit from either `Handler` (sync) or `AsyncHandler` (async):

```python
from cqrs_framing import Handler, AsyncHandler, CancellationToken

# Synchronous handler
class MySyncHandler(Handler[MyCommand, str]):
    def execute(self, message: MyCommand) -> str:
        return "result"

# Asynchronous handler
class MyAsyncHandler(AsyncHandler[MyCommand, str]):
    async def execute(self, message: MyCommand, cancellation_token: CancellationToken) -> str:
        return "result"
```

**Why inheritance is required:**
- ✅ Clear contract discovery in IDEs (autocomplete, hints)
- ✅ Type checker enforcement (mypy/Pylance catches errors)
- ✅ Registration-time validation (fails fast if signature is wrong)
- ✅ Prevents accidental direct invocation bypassing the broker

### Define Messages and Handlers

```python
from cqrs_framing import Message, AsyncHandler, CommandResponse, Response, CancellationToken
from dataclasses import dataclass

@dataclass
class CreateUser(Message):
    username: str
    email: str

class CreateUserHandler(AsyncHandler[CreateUser, CommandResponse[str]]):
    async def execute(self, message: CreateUser, cancellation_token: CancellationToken) -> CommandResponse[str]:
        # Your business logic here
        user_id = f"user-{message.username}"
        return Response.ok(user_id)
```

### Register and Execute

```python
from cqrs_framing import Broker, HandlerRegistry

# Setup
registry = HandlerRegistry()
broker = Broker(registry)

# Register handler (will be auto-instantiated by DI)
registry.register(CreateUser, CreateUserHandler)

# Execute command
result = await broker.handle_async(CreateUser(username="john", email="john@example.com"))
```

## Async and sync semantics

- Prefer `Broker.handle_async(...)` in async applications.
- `Broker.handle(...)` is for synchronous handlers. If you provide a `sync_pipeline`, it requires creating an event loop internally; calling it from within an already-running event loop will raise a `RuntimeError`.
- `Event.fire(...)` / `EventHub.publish(...)` are fire-and-forget. If you subscribe any async handlers, publish from an async context or use `fire_async(...)` / `publish_async(...)`.

### Handlers with Dependencies

```python
class UserRepository:
    def save(self, user): ...

class CreateUserHandler(AsyncHandler[CreateUser, CommandResponse[str]]):
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    async def execute(self, message: CreateUser, cancellation_token) -> CommandResponse[str]:
        # Dependencies are auto-injected!
        user_id = f"user-{message.username}"
        self.repository.save({"id": user_id, "username": message.username})
        return Response.ok(user_id)

# Register service in DI container
registry.container.register_instance(UserRepository, UserRepository())

# Register handler (repository will be injected)
registry.register(CreateUser, CreateUserHandler)
```

### Domain Events

```python
from cqrs_framing import AggregateRoot, DomainEvent, EventHub
from dataclasses import dataclass

@dataclass
class UserCreated(DomainEvent):
    user_id: str
    email: str

class User(AggregateRoot):
    def __init__(self, user_id: str, email: str):
        super().__init__()
        self.user_id = user_id
        self.email = email
        self._raise(UserCreated(user_id=user_id, email=email))

# Subscribe to events
hub = EventHub()

def send_welcome_email(event: UserCreated):
    print(f"Sending welcome email to {event.email}")

hub[UserCreated] += send_welcome_email

# Publish events
user = User("123", "john@example.com")
for event in user.pending_events:
    hub.publish(event)
```

## Requirements

- Python >= 3.10

## License

MIT
