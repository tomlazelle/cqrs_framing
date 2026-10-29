"""Integration test demonstrating full CQRS flow."""

from dataclasses import dataclass

import pytest

from cqrs_framing import (
    AggregateRoot,
    AsyncHandler,
    Broker,
    CommandResponse,
    DomainEvent,
    DomainEventDispatcher,
    EventHub,
    HandlerRegistry,
    Message,
    Response,
)


# Domain Events
@dataclass
class UserCreated(DomainEvent):
    user_id: str
    username: str
    email: str


@dataclass
class UserUpdated(DomainEvent):
    user_id: str
    username: str


# Aggregates
class User(AggregateRoot):
    def __init__(self, user_id: str, username: str, email: str):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.email = email
        self._raise(UserCreated(user_id=user_id, username=username, email=email))

    def update_username(self, new_username: str):
        self.username = new_username
        self._raise(UserUpdated(user_id=self.user_id, username=new_username))


# Commands
@dataclass
class CreateUserCommand(Message):
    user_id: str
    username: str
    email: str


@dataclass
class UpdateUsernameCommand(Message):
    user_id: str
    new_username: str


# Queries
@dataclass
class GetUserQuery(Message):
    user_id: str


# In-memory repository
class UserRepository:
    def __init__(self):
        self._users = {}

    def save(self, user: User):
        self._users[user.user_id] = user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)


# Handlers
class CreateUserHandler(AsyncHandler[CreateUserCommand, User]):
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def execute(self, command: CreateUserCommand, cancellation_token) -> User:
        user = User(command.user_id, command.username, command.email)
        self.repository.save(user)
        return user


class UpdateUsernameHandler(AsyncHandler[UpdateUsernameCommand, CommandResponse[User]]):
    def __init__(self, repository: UserRepository, dispatcher: DomainEventDispatcher):
        self.repository = repository
        self.dispatcher = dispatcher

    async def execute(
        self, command: UpdateUsernameCommand, cancellation_token
    ) -> CommandResponse[User]:
        user = self.repository.get(command.user_id)
        if user is None:
            return Response.failed(f"User {command.user_id} not found")
        user.update_username(command.new_username)
        self.repository.save(user)
        # Manually dispatch events from the aggregate
        await self.dispatcher.dispatch_from_async(user)
        return Response.ok(user)


class GetUserHandler(AsyncHandler[GetUserQuery, CommandResponse[User]]):
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def execute(
        self, query: GetUserQuery, cancellation_token
    ) -> CommandResponse[User]:
        user = self.repository.get(query.user_id)
        if user is None:
            return Response.failed(f"User {query.user_id} not found")
        return Response.ok(user)


@pytest.mark.asyncio
async def test_full_cqrs_flow():
    """Integration test for complete CQRS flow with domain events."""
    # Setup
    repository = UserRepository()
    registry = HandlerRegistry()
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    broker = Broker(registry, domain_dispatcher=dispatcher)

    # Register services in DI container
    registry.container.register_instance(UserRepository, repository)
    registry.container.register_instance(DomainEventDispatcher, dispatcher)

    # Register handlers (will be resolved with dependencies)
    registry.register(CreateUserCommand, CreateUserHandler)
    registry.register(UpdateUsernameCommand, UpdateUsernameHandler)
    registry.register(GetUserQuery, GetUserHandler)

    # Track events
    events_received = []

    def on_user_created(event: UserCreated):
        events_received.append(("created", event.user_id, event.username))

    def on_user_updated(event: UserUpdated):
        events_received.append(("updated", event.user_id, event.username))

    hub[UserCreated] += on_user_created
    hub[UserUpdated] += on_user_updated

    # Execute create command
    user = await broker.handle_async(
        CreateUserCommand(user_id="123", username="john", email="john@example.com")
    )

    assert isinstance(user, User)
    assert user.user_id == "123"
    assert user.username == "john"
    assert len(events_received) == 1
    assert events_received[0] == ("created", "123", "john")

    # Execute query
    query_result = await broker.handle_async(GetUserQuery(user_id="123"))

    assert query_result.success is True
    assert query_result.data.username == "john"

    # Execute update command
    update_result = await broker.handle_async(
        UpdateUsernameCommand(user_id="123", new_username="john_doe")
    )

    assert update_result.success is True
    assert update_result.data.username == "john_doe"
    assert len(events_received) == 2
    assert events_received[1] == ("updated", "123", "john_doe")

    # Verify update persisted
    query_result2 = await broker.handle_async(GetUserQuery(user_id="123"))
    assert query_result2.data.username == "john_doe"


@pytest.mark.asyncio
async def test_command_failure():
    """Test handling of failed commands."""
    repository = UserRepository()
    registry = HandlerRegistry()
    hub = EventHub()
    dispatcher = DomainEventDispatcher(hub)
    broker = Broker(registry)

    # Register services
    registry.container.register_instance(UserRepository, repository)
    registry.container.register_instance(DomainEventDispatcher, dispatcher)

    # Register handler
    registry.register(UpdateUsernameCommand, UpdateUsernameHandler)

    # Try to update non-existent user
    result = await broker.handle_async(
        UpdateUsernameCommand(user_id="999", new_username="test")
    )

    assert result.success is False
    assert "not found" in result.message
