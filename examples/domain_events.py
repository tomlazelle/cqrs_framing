"""Example: Domain events with aggregates."""

import asyncio
from dataclasses import dataclass

from cqrs_framing import (
    AggregateRoot,
    Broker,
    CommandResponse,
    DomainEvent,
    DomainEventDispatcher,
    EventHub,
    HandlerRegistry,
    Message,
    Response,
)
from cqrs_framing.handlers import AsyncHandler


# Domain Events
@dataclass
class OrderCreated(DomainEvent):
    """Event raised when an order is created."""

    order_id: str
    customer_name: str
    total: float


@dataclass
class OrderShipped(DomainEvent):
    """Event raised when an order is shipped."""

    order_id: str
    tracking_number: str


# Aggregate
class Order(AggregateRoot):
    """Order aggregate root."""

    def __init__(self, order_id: str, customer_name: str, total: float):
        super().__init__()
        self.order_id = order_id
        self.customer_name = customer_name
        self.total = total
        self.shipped = False
        self.tracking_number = None

        # Raise domain event
        self._raise(
            OrderCreated(order_id=order_id, customer_name=customer_name, total=total)
        )

    def ship(self, tracking_number: str):
        """Ship the order."""
        if self.shipped:
            raise ValueError("Order already shipped")

        self.shipped = True
        self.tracking_number = tracking_number

        # Raise domain event
        self._raise(
            OrderShipped(order_id=self.order_id, tracking_number=tracking_number)
        )


# Commands
@dataclass
class CreateOrder(Message):
    """Command to create an order."""

    order_id: str
    customer_name: str
    total: float


@dataclass
class ShipOrder(Message):
    """Command to ship an order."""

    order_id: str
    tracking_number: str


# Repository
class OrderRepository:
    """In-memory order repository."""

    def __init__(self):
        self._orders = {}

    def save(self, order: Order):
        """Save an order."""
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        """Get an order by ID."""
        return self._orders.get(order_id)


# Handlers
class CreateOrderHandler(AsyncHandler[CreateOrder, Order]):
    """Handler for creating orders."""

    def __init__(self, repository: OrderRepository):
        self.repository = repository

    async def execute(self, command: CreateOrder, cancellation_token) -> Order:
        """Execute the create order command."""
        order = Order(command.order_id, command.customer_name, command.total)
        self.repository.save(order)
        return order


class ShipOrderHandler(AsyncHandler[ShipOrder, CommandResponse[Order]]):
    """Handler for shipping orders."""

    def __init__(self, repository: OrderRepository, dispatcher: DomainEventDispatcher):
        self.repository = repository
        self.dispatcher = dispatcher

    async def execute(
        self, command: ShipOrder, cancellation_token
    ) -> CommandResponse[Order]:
        """Execute the ship order command."""
        order = self.repository.get(command.order_id)
        if order is None:
            return Response.failed(f"Order {command.order_id} not found")

        try:
            order.ship(command.tracking_number)
            self.repository.save(order)
            # Dispatch events from the aggregate
            await self.dispatcher.dispatch_from_async(order)
            return Response.ok(order)
        except ValueError as e:
            return Response.failed(str(e))


# Event Handlers
class EmailService:
    """Service for sending emails."""

    def on_order_created(self, event: OrderCreated):
        """Send confirmation email when order is created."""
        print(f"📧 Sending order confirmation email to {event.customer_name}")
        print(f"   Order ID: {event.order_id}, Total: ${event.total:.2f}")

    async def on_order_shipped(self, event: OrderShipped):
        """Send shipping notification when order is shipped."""
        print("📧 Sending shipping notification")
        print(f"   Order ID: {event.order_id}, " f"Tracking: {event.tracking_number}")


class InventoryService:
    """Service for managing inventory."""

    def on_order_created(self, event: OrderCreated):
        """Reserve inventory when order is created."""
        print(f"📦 Reserving inventory for order {event.order_id}")


class LoggingService:
    """Service for logging events."""

    def on_order_created(self, event: OrderCreated):
        """Log order creation."""
        print(f"📝 LOG: Order created - {event.order_id}")

    def on_order_shipped(self, event: OrderShipped):
        """Log order shipping."""
        print(f"📝 LOG: Order shipped - {event.order_id}")


async def main():
    """Run the example."""
    print("=== Domain Events Example ===\n")

    # Setup
    repository = OrderRepository()
    registry = HandlerRegistry()
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    broker = Broker(registry, domain_dispatcher=dispatcher)

    # Register services in DI container
    registry.container.register_instance(OrderRepository, repository)
    registry.container.register_instance(DomainEventDispatcher, dispatcher)

    # Register handlers (dependencies will be auto-injected)
    registry.register(CreateOrder, CreateOrderHandler)
    registry.register(ShipOrder, ShipOrderHandler)

    # Register event handlers
    email_service = EmailService()
    inventory_service = InventoryService()
    logging_service = LoggingService()

    hub[OrderCreated] += email_service.on_order_created
    hub[OrderCreated] += inventory_service.on_order_created
    hub[OrderCreated] += logging_service.on_order_created
    hub[OrderShipped] += email_service.on_order_shipped
    hub[OrderShipped] += logging_service.on_order_shipped

    # Create an order
    print("Creating order...\n")
    order = await broker.handle_async(
        CreateOrder(order_id="ORD-001", customer_name="John Doe", total=149.99)
    )
    print(f"\n✓ Order created: {order.order_id}\n")

    # Ship the order
    print("Shipping order...\n")
    result = await broker.handle_async(
        ShipOrder(order_id="ORD-001", tracking_number="TRACK-123456")
    )
    print(f"\n✓ Order shipped: {result.data.tracking_number}\n")

    # Try to ship again (should fail)
    print("Trying to ship again...\n")
    result2 = await broker.handle_async(
        ShipOrder(order_id="ORD-001", tracking_number="TRACK-999999")
    )
    print(f"✗ Failed as expected: {result2.message}\n")


if __name__ == "__main__":
    asyncio.run(main())
