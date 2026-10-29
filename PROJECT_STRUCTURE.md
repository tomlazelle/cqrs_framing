# CQRS Framing - Project Structure

## Overview

This is a Python implementation of a CQRS (Command Query Responsibility Segregation) framework with first-class domain events support, inspired by .NET's CommandQuery.Framing.

## Project Structure

```
python_cqrs/
├── src/
│   └── cqrs_framing/           # Main package
│       ├── __init__.py          # Public API exports
│       ├── py.typed             # Type marker file
│       ├── broker.py            # Central command/query broker
│       ├── cancellation.py      # Cancellation token
│       ├── context.py           # Handler execution contexts
│       ├── decorators.py        # Decorator-based registration
│       ├── dispatcher.py        # Domain event dispatcher
│       ├── domain.py            # Aggregate root and domain events
│       ├── events.py            # Event system (Event, EventHub)
│       ├── handlers.py          # Handler protocols
│       ├── messages.py          # Message base class
│       ├── pipeline.py          # Middleware pipeline
│       ├── registry.py          # Handler registry
│       └── responses.py         # Command responses
├── Tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── test_broker.py           # Broker tests
│   ├── test_cancellation.py    # Cancellation tests
│   ├── test_decorators.py      # Decorator tests
│   ├── test_dispatcher.py      # Dispatcher tests
│   ├── test_domain.py           # Domain model tests
│   ├── test_events.py           # Event system tests
│   ├── test_integration.py     # Integration tests
│   ├── test_pipeline.py        # Pipeline tests
│   ├── test_registry.py        # Registry tests
│   └── test_responses.py       # Response tests
├── examples/
│   ├── __init__.py
│   ├── basic_usage.py          # Basic CQRS example
│   ├── domain_events.py        # Domain events example
│   └── middleware_pipeline.py  # Middleware example
├── pyproject.toml              # Project metadata and build config
├── requirements-dev.txt        # Development dependencies
├── README.md                   # Project documentation
└── .gitignore                  # Git ignore rules
```

## Key Components

### Core Abstractions

1. **Message**: Base class for all commands and queries
2. **Handler/AsyncHandler**: Abstract base classes that all handlers must inherit from
3. **HandlerRegistry**: Maps request types to handlers using DI container
4. **Broker**: Central dispatcher for commands and queries

**Handler Contract:**
All handlers must inherit from `Handler` (sync) or `AsyncHandler` (async) and implement the `execute` method:

```python
from cqrs_framing import AsyncHandler, CancellationToken

class MyCommandHandler(AsyncHandler[MyCommand, MyResponse]):
    async def execute(self, message: MyCommand, cancellation_token: CancellationToken) -> MyResponse:
        # Handler logic
        pass
```

This inheritance requirement ensures:
- IDE support (autocomplete, type hints)
- Type checking validation
- Registration-time signature verification
- Protection against accidental direct handler invocation

### Dependency Injection

The framework uses [di-done-right](https://pypi.org/project/di-done-right/) for dependency injection:

1. **DIContainer**: Service container for resolving dependencies
2. **HandlerRegistry**: Wraps the DI container for handler registration
3. **Auto-injection**: Handler dependencies are automatically resolved

Example:
```python
registry = HandlerRegistry()

# Register a service
registry.container.register_instance(MyService, MyService())

# Register handler (service will be auto-injected)
registry.register(MyCommand, MyCommandHandler)
```

### Domain Events

1. **DomainEvent**: Base class for domain events
2. **AggregateRoot**: Base class for aggregates that raise events
3. **DomainEventDispatcher**: Dispatches events from aggregates
4. **Event/EventHub**: Delegate-style event system with `+=` / `-=` syntax

### Pipeline

1. **Pipeline**: Middleware pipeline for cross-cutting concerns
2. **HandlerContext/AsyncHandlerContext**: Execution contexts

### Responses

1. **CommandResponse**: Generic response wrapper
2. **Response**: Factory for creating responses (ok/failed)

## Running Tests

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

Run all tests:
```bash
pytest Tests/
```

Run with coverage:
```bash
pytest Tests/ --cov=cqrs_framing
```

## Running Examples

All examples are runnable Python scripts:

```bash
# Basic CQRS usage
python examples/basic_usage.py

# Domain events demonstration
python examples/domain_events.py

# Middleware pipeline
python examples/middleware_pipeline.py
```

## Installation for Development

Install the package in editable mode:
```bash
pip install -e .
```

## Design Principles

1. **Type Safety**: Full type hints throughout
2. **Framework Agnostic**: No dependency on web frameworks
3. **Async First**: Built for async/await patterns
4. **Extensible**: Pipeline middleware for cross-cutting concerns
5. **Clean Separation**: Clear boundaries between commands, queries, and events

## Usage Pattern

```python
from cqrs_framing import (
    AsyncHandler,
    Broker,
    CancellationToken,
    CommandResponse,
    HandlerRegistry,
    Message,
    Response,
)

# 1. Define your message
class CreateUser(Message):
    def __init__(self, username: str):
        self.username = username

# 2. Define your handler (must inherit from AsyncHandler)
class CreateUserHandler(AsyncHandler[CreateUser, CommandResponse[str]]):
    async def execute(self, command: CreateUser, cancellation_token: CancellationToken) -> CommandResponse[str]:
        # Business logic here
        return Response.ok(f"User {command.username} created")

# 3. Register and execute
registry = HandlerRegistry()
registry.register(CreateUser, CreateUserHandler)
broker = Broker(registry)

result = await broker.handle_async(CreateUser("john"))
```

## Next Steps

- [ ] Add more middleware examples (validation, logging, metrics)
- [ ] Add outbox pattern implementation
- [ ] Add FastAPI integration adapter
- [ ] Add documentation site
- [ ] Publish to PyPI
