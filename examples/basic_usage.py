"""Example: Basic CQRS usage with commands and queries."""

import asyncio
from dataclasses import dataclass

from cqrs_framing import (
    Broker,
    CommandResponse,
    HandlerRegistry,
    Message,
    Response,
)
from cqrs_framing.handlers import AsyncHandler


# Define commands
@dataclass
class CreateProduct(Message):
    """Command to create a new product."""

    product_id: str
    name: str
    price: float


@dataclass
class GetProduct(Message):
    """Query to get a product by ID."""

    product_id: str


# Simple in-memory storage
products = {}


# Define handlers
class CreateProductHandler(AsyncHandler[CreateProduct, CommandResponse[str]]):
    """Handler for creating products."""

    async def execute(
        self, command: CreateProduct, cancellation_token
    ) -> CommandResponse[str]:
        """Execute the create product command."""
        if command.product_id in products:
            return Response.failed(f"Product {command.product_id} already exists")

        products[command.product_id] = {
            "name": command.name,
            "price": command.price,
        }
        print(f"✓ Created product: {command.name} (${command.price})")
        return Response.ok(command.product_id)


class GetProductHandler(AsyncHandler[GetProduct, dict]):
    """Handler for retrieving products."""

    async def execute(
        self, query: GetProduct, cancellation_token
    ) -> CommandResponse[dict]:
        """Execute the get product query."""
        product = products.get(query.product_id)
        if product is None:
            return Response.failed(f"Product {query.product_id} not found")

        print(f"✓ Retrieved product: {product['name']} (${product['price']})")
        return Response.ok(product)


async def main():
    """Run the example."""
    print("=== Basic CQRS Example ===\n")

    # Setup
    registry = HandlerRegistry()
    broker = Broker(registry)

    # Register handlers (will be auto-instantiated by DI)
    registry.register(CreateProduct, CreateProductHandler)
    registry.register(GetProduct, GetProductHandler)

    # Create some products
    print("Creating products...")
    result1 = await broker.handle_async(
        CreateProduct(product_id="1", name="Laptop", price=999.99)
    )
    result2 = await broker.handle_async(
        CreateProduct(product_id="2", name="Mouse", price=29.99)
    )

    print(f"\nResults: {result1.success}, {result2.success}")

    # Try to create duplicate (should fail)
    print("\nTrying to create duplicate product...")
    result3 = await broker.handle_async(
        CreateProduct(product_id="1", name="Duplicate", price=0)
    )
    print(f"Failed as expected: {result3.message}")

    # Query products
    print("\nQuerying products...")
    product1 = await broker.handle_async(GetProduct(product_id="1"))
    product2 = await broker.handle_async(GetProduct(product_id="2"))

    print(f"\nProduct 1: {product1.data}")
    print(f"Product 2: {product2.data}")

    # Try to query non-existent product
    print("\nQuerying non-existent product...")
    result4 = await broker.handle_async(GetProduct(product_id="999"))
    print(f"Failed as expected: {result4.message}")


if __name__ == "__main__":
    asyncio.run(main())
