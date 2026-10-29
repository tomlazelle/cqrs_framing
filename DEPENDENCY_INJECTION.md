# Dependency Injection with di-done-right

CQRS Framing uses [di-done-right](https://pypi.org/project/di-done-right/) for dependency injection, providing automatic resolution of handler dependencies.

## Quick Start

### Simple Handler (No Dependencies)

```python
from cqrs_framing import Broker, HandlerRegistry, Message, Response

class CreateProduct(Message):
    name: str
    price: float

class CreateProductHandler:
    async def execute(self, message: CreateProduct, cancellation_token) -> CommandResponse[str]:
        return Response.ok(f"product-{message.name}")

# Register handler type (will be auto-instantiated)
registry = HandlerRegistry()
registry.register(CreateProduct, CreateProductHandler)
```

### Handler with Dependencies

```python
class ProductRepository:
    def save(self, name: str, price: float) -> str:
        # Save to database
        return f"product-{name}"

class CreateProductHandler:
    def __init__(self, repository: ProductRepository):
        self.repository = repository
    
    async def execute(self, message: CreateProduct, cancellation_token) -> CommandResponse[str]:
        product_id = self.repository.save(message.name, message.price)
        return Response.ok(product_id)

# Register service in DI container
registry.container.register_instance(ProductRepository, ProductRepository())

# Register handler (repository will be auto-injected)
registry.register(CreateProduct, CreateProductHandler)
```

## Registration Methods

### `registry.register(message_type, handler_type)`

Registers a handler **type** (class) that will be instantiated by the DI container when needed:

```python
# Handler will be created on first use
registry.register(CreateProduct, CreateProductHandler)
```

Dependencies are automatically resolved from the container.

### `registry.register_instance(message_type, handler_instance)`

Registers a pre-instantiated handler **instance**:

```python
# Handler instance is created manually
handler = CreateProductHandler(ProductRepository())
registry.register_instance(CreateProduct, handler)
```

Use this when you need manual control over handler instantiation.

### `registry.container.register_instance(service_type, service_instance)`

Registers a service instance in the DI container for injection:

```python
# Service available for injection into handlers
registry.container.register_instance(ProductRepository, ProductRepository())
```

## Accessing the DI Container

The `HandlerRegistry` wraps a `DIContainer` instance:

```python
from di_container.container import DIContainer

# Create registry with custom container
container = DIContainer()
registry = HandlerRegistry(container)

# Or access the default container
registry.container.register_instance(MyService, MyService())
```

## Multiple Dependencies

Handlers can have multiple constructor dependencies:

```python
class CreateOrderHandler:
    def __init__(
        self, 
        order_repo: OrderRepository,
        email_service: EmailService,
        logger: Logger
    ):
        self.order_repo = order_repo
        self.email_service = email_service
        self.logger = logger
    
    async def execute(self, message: CreateOrder, cancellation_token) -> CommandResponse[str]:
        order_id = self.order_repo.save(message.items)
        await self.email_service.send_confirmation(message.customer_email)
        self.logger.info(f"Order created: {order_id}")
        return Response.ok(order_id)

# Register all services
registry.container.register_instance(OrderRepository, OrderRepository())
registry.container.register_instance(EmailService, EmailService())
registry.container.register_instance(Logger, Logger())

# Register handler (all dependencies auto-injected)
registry.register(CreateOrder, CreateOrderHandler)
```

## Benefits

- **Separation of Concerns**: Business logic separated from object construction
- **Testability**: Easy to mock dependencies in tests
- **Flexibility**: Switch implementations without changing handlers
- **Maintainability**: Clear dependency declarations in constructor

## Testing with DI

```python
import pytest
from unittest.mock import Mock

def test_create_product_handler():
    # Mock the repository
    mock_repo = Mock(spec=ProductRepository)
    mock_repo.save.return_value = "product-123"
    
    # Register mock in container
    registry = HandlerRegistry()
    registry.container.register_instance(ProductRepository, mock_repo)
    registry.register(CreateProduct, CreateProductHandler)
    
    broker = Broker(registry)
    result = await broker.handle_async(CreateProduct(name="Laptop", price=999.99))
    
    assert result.is_successful
    assert result.data == "product-123"
    mock_repo.save.assert_called_once_with("Laptop", 999.99)
```

## Advanced Patterns

### Factory Pattern

```python
class HandlerFactory:
    def __init__(self, config: Config):
        self.config = config
    
    def create_handler(self) -> CreateProductHandler:
        if self.config.use_caching:
            return CachedProductHandler(ProductRepository())
        return CreateProductHandler(ProductRepository())

registry.container.register_instance(Config, Config(use_caching=True))
registry.container.register_instance(HandlerFactory, HandlerFactory)
```

### Scoped Services

For request-scoped or transient dependencies, create a new container per request:

```python
def handle_request(message):
    # Create scoped container
    scoped_container = DIContainer()
    scoped_container.register_instance(RequestContext, RequestContext(user_id=123))
    
    # Create registry with scoped container
    registry = HandlerRegistry(scoped_container)
    registry.register(CreateProduct, CreateProductHandler)
    
    broker = Broker(registry)
    return await broker.handle_async(message)
```

## See Also

- [di-done-right documentation](https://pypi.org/project/di-done-right/)
- [QUICKSTART.md](QUICKSTART.md) for basic examples
- [examples/basic_usage.py](examples/basic_usage.py) for working code
