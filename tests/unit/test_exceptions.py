"""Tests for KIS exception classes.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

import pytest

from stock_manager.adapters.broker.kis.exceptions import (
    KISException,
    KISConfigurationError,
    KISAuthenticationError,
    KISAPIError,
    KISRateLimitError,
    KISValidationError,
)


class TestKISException:
    """Tests for base KISException."""

    def test_exception_with_message(self) -> None:
        """Test exception with message only."""
        exc = KISException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.error_code is None

    def test_exception_with_message_and_error_code(self) -> None:
        """Test exception with message and error code."""
        exc = KISException("Test error", error_code="EGW001")

        assert str(exc) == "[EGW001] Test error"
        assert exc.message == "Test error"
        assert exc.error_code == "EGW001"

    def test_exception_is_catchable_as_base(self) -> None:
        """Test all KIS exceptions inherit from KISException."""
        exc1 = KISConfigurationError("Config error")
        exc2 = KISAuthenticationError("Auth error")
        exc3 = KISAPIError("API error")
        exc4 = KISRateLimitError("Rate limit")
        exc5 = KISValidationError("Validation error")

        assert isinstance(exc1, KISException)
        assert isinstance(exc2, KISException)
        assert isinstance(exc3, KISException)
        assert isinstance(exc4, KISException)
        assert isinstance(exc5, KISException)

    def test_exception_raising_and_catching(self) -> None:
        """Test exception can be raised and caught."""
        with pytest.raises(KISException, match="Test error"):
            raise KISException("Test error")


class TestKISConfigurationError:
    """Tests for KISConfigurationError."""

    def test_configuration_error_creation(self) -> None:
        """Test creating configuration error."""
        exc = KISConfigurationError("Missing API key")

        assert isinstance(exc, KISException)
        assert str(exc) == "Missing API key"

    def test_configuration_error_with_code(self) -> None:
        """Test configuration error with error code."""
        exc = KISConfigurationError("Invalid config", error_code="CONFIG001")

        assert str(exc) == "[CONFIG001] Invalid config"


class TestKISAuthenticationError:
    """Tests for KISAuthenticationError."""

    def test_authentication_error_creation(self) -> None:
        """Test creating authentication error."""
        exc = KISAuthenticationError("Invalid credentials")

        assert isinstance(exc, KISException)
        assert str(exc) == "Invalid credentials"

    def test_authentication_error_with_code(self) -> None:
        """Test authentication error with error code."""
        exc = KISAuthenticationError(
            "Token expired",
            error_code="EGW00001",
        )

        assert str(exc) == "[EGW00001] Token expired"


class TestKISAPIError:
    """Tests for KISAPIError."""

    def test_api_error_creation(self) -> None:
        """Test creating API error with minimal args."""
        exc = KISAPIError("API request failed")

        assert isinstance(exc, KISException)
        assert str(exc) == "API request failed"
        assert exc.status_code is None
        assert exc.response_data is None

    def test_api_error_with_all_fields(self) -> None:
        """Test creating API error with all fields."""
        response_data = {"error": "details"}
        exc = KISAPIError(
            message="API request failed",
            error_code="EGW002",
            status_code=400,
            response_data=response_data,
        )

        assert exc.error_code == "EGW002"
        assert exc.status_code == 400
        assert exc.response_data is response_data

    def test_api_error_string_with_status(self) -> None:
        """Test API error string representation with status code."""
        exc = KISAPIError(
            message="Not found",
            status_code=404,
            error_code="EGW404",
        )

        error_str = str(exc)

        assert "[EGW404]" in error_str
        assert "(HTTP 404)" in error_str
        assert "Not found" in error_str

    def test_api_error_string_without_status(self) -> None:
        """Test API error string representation without status code."""
        exc = KISAPIError(message="Generic error")

        assert str(exc) == "Generic error"


class TestKISRateLimitError:
    """Tests for KISRateLimitError."""

    def test_rate_limit_error_creation(self) -> None:
        """Test creating rate limit error."""
        exc = KISRateLimitError("Too many requests")

        assert isinstance(exc, KISAPIError)
        assert isinstance(exc, KISException)
        assert str(exc) == "Too many requests"

    def test_rate_limit_error_with_status(self) -> None:
        """Test rate limit error with HTTP status."""
        exc = KISRateLimitError(
            "Rate limit exceeded",
            status_code=429,
            error_code="EGW00108",
        )

        assert exc.status_code == 429
        assert "(HTTP 429)" in str(exc)


class TestKISValidationError:
    """Tests for KISValidationError."""

    def test_validation_error_creation(self) -> None:
        """Test creating validation error."""
        exc = KISValidationError("Invalid parameter")

        assert isinstance(exc, KISException)
        assert str(exc) == "Invalid parameter"

    def test_validation_error_with_code(self) -> None:
        """Test validation error with error code."""
        exc = KISValidationError(
            "Missing required field",
            error_code="VALIDATION001",
        )

        assert str(exc) == "[VALIDATION001] Missing required field"


class TestExceptionHierarchy:
    """Tests for exception hierarchy and relationships."""

    def test_all_exceptions_have_message(self) -> None:
        """Test all KIS exceptions can be created with message."""
        exceptions = [
            KISException,
            KISConfigurationError,
            KISAuthenticationError,
            KISAPIError,
            KISRateLimitError,
            KISValidationError,
        ]

        for exc_class in exceptions:
            exc = exc_class("Test message")
            assert exc.message == "Test message"

    def test_specific_errors_are_not_generic_errors(self) -> None:
        """Test specific error types are not caught by generic types incorrectly."""
        exc = KISRateLimitError("Rate limit")

        assert isinstance(exc, KISAPIError)  # Rate limit IS an API error
        assert isinstance(exc, KISException)  # Rate limit IS a KIS exception
        assert not isinstance(exc, KISValidationError)  # But NOT a validation error

    def test_catching_base_exception(self) -> None:
        """Test all specific errors can be caught as KISException."""
        specific_errors = [
            KISConfigurationError("config"),
            KISAuthenticationError("auth"),
            KISAPIError("api"),
            KISRateLimitError("rate"),
            KISValidationError("validation"),
        ]

        caught_count = 0

        for error in specific_errors:
            try:
                raise error
            except KISException:
                caught_count += 1

        assert caught_count == len(specific_errors)


class TestExceptionUseCases:
    """Tests for real-world exception use cases."""

    def test_missing_api_key_error(self) -> None:
        """Test error for missing API key."""
        exc = KISConfigurationError(
            "KIS_APP_KEY environment variable is not set",
            error_code="CONFIG001",
        )

        assert "KIS_APP_KEY" in str(exc)
        assert exc.error_code == "CONFIG001"

    def test_invalid_credentials_error(self) -> None:
        """Test error for invalid credentials."""
        exc = KISAuthenticationError(
            "Authentication failed: Invalid APP_KEY or APP_SECRET",
            error_code="EGW00001",
        )

        assert "Authentication failed" in str(exc)
        assert exc.error_code == "EGW00001"

    def test_rate_limit_exceeded_error(self) -> None:
        """Test error for rate limit."""
        exc = KISRateLimitError(
            "Exceeds the daily request limit",
            status_code=429,
            error_code="EGW00108",
        )

        assert exc.status_code == 429
        assert "daily request limit" in str(exc)

    def test_invalid_stock_symbol_error(self) -> None:
        """Test error for invalid stock symbol."""
        exc = KISValidationError(
            "Invalid stock symbol: INVALID",
            error_code="EGW00223",
        )

        assert "Invalid stock symbol" in str(exc)
        assert exc.error_code == "EGW00223"

    def test_network_error_wrapper(self) -> None:
        """Test wrapping network error in KISAPIError."""
        exc = KISAPIError(
            "Network error during API request",
            status_code=None,
        )

        assert "Network error" in str(exc)
