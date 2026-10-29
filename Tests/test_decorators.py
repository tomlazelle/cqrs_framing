"""Tests for decorators."""

import pytest

from cqrs_framing import (
    Handler,
    HandlerRegistry,
    Message,
    handler,
    set_default_registry,
)


class DecoratorTestCommand(Message):
    pass


def test_handler_decorator_registration():
    """Test decorator-based handler registration."""
    registry = HandlerRegistry()
    set_default_registry(registry)

    @handler(DecoratorTestCommand)
    class TestHandler(Handler[DecoratorTestCommand, str]):
        def execute(self, message: DecoratorTestCommand) -> str:
            return "handled"

    # Handler should be registered
    resolved = registry.resolve_sync(DecoratorTestCommand)
    assert resolved is not None
    assert resolved.execute(DecoratorTestCommand()) == "handled"


def test_handler_decorator_without_registry():
    """Test that decorator raises error if registry not set."""
    # Reset global registry
    import cqrs_framing.decorators

    cqrs_framing.decorators._registry_singleton = None

    class AnotherCommand(Message):
        pass

    with pytest.raises(RuntimeError, match="Default registry not set"):

        @handler(AnotherCommand)
        class TestHandler(Handler[AnotherCommand, str]):
            def execute(self, message: AnotherCommand) -> str:
                return "handled"


def test_handler_decorator_creates_instance():
    registry = HandlerRegistry()
    set_default_registry(registry)

    class YetAnotherCommand(Message):
        pass

    @handler(YetAnotherCommand)
    class TestHandler(Handler[YetAnotherCommand, str]):
        def __init__(self):
            self.created = True

        def execute(self, message: YetAnotherCommand) -> str:
            return "handled"

    resolved = registry.resolve_sync(YetAnotherCommand)
    assert hasattr(resolved, "created")
    assert resolved.created is True
