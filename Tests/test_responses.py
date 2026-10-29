"""Tests for command responses."""

from cqrs_framing import CommandResponse, Response


def test_response_ok_with_data():
    """Test creating a successful response with data."""
    response = Response.ok("test data")

    assert response.success is True
    assert response.data == "test data"
    assert response.raw_data == "test data"
    assert response.message is None
    assert response.exception is None


def test_response_ok_without_data():
    """Test creating a successful response without data."""
    response = Response.ok()

    assert response.success is True
    assert response.data is None
    assert response.raw_data is None


def test_response_failed_with_string():
    """Test creating a failed response with string message."""
    response = Response.failed("error message")

    assert response.success is False
    assert response.message == "error message"
    assert response.data is None
    assert response.exception is None


def test_response_failed_with_list():
    """Test creating a failed response with list of messages."""
    response = Response.failed(["error1", "error2", "error3"])

    assert response.success is False
    assert response.message == "error1 error2 error3"


def test_response_failed_with_exception():
    """Test creating a failed response with exception."""
    ex = ValueError("test error")
    response = Response.failed("error occurred", exception=ex)

    assert response.success is False
    assert response.message == "error occurred"
    assert response.exception is ex


def test_command_response_raw_data():
    """Test CommandResponse raw_data property."""
    response = CommandResponse(success=True, data="test")

    assert response.raw_data == "test"
