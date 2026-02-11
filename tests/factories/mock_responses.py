"""Mock response factory for httpx responses in tests.

This module provides factory functions for creating mock httpx.Response
objects, following Kent Beck's TDD principle of simple, testable code.
"""

from typing import Any
from unittest.mock import MagicMock

import httpx
from httpx import Response


class MockResponseFactory:
    """Factory for creating mock httpx.Response objects.

    Provides convenient methods for creating various HTTP responses
    that simulate KIS API behavior in tests.
    """

    @staticmethod
    def success(data: dict[str, Any] | None = None) -> MagicMock:
        """Create a mock success response (HTTP 200).

        Args:
            data: Response JSON data (default: empty dict)

        Returns:
            Mock httpx.Response with status 200
        """
        if data is None:
            data = {}

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = data
        mock_response.raise_for_status = MagicMock()
        mock_response.text = str(data)

        # Add reason_phrase
        mock_response.reason_phrase = "OK"

        return mock_response

    @staticmethod
    def success_kis(output: dict[str, Any] | None = None) -> MagicMock:
        """Create a mock KIS API success response.

        KIS API returns rt_cd="0" for success.

        Args:
            output: Output data (default: empty dict)

        Returns:
            Mock response with KIS success structure
        """
        if output is None:
            output = {}

        data = {
            "rt_cd": "0",
            "msg_cd": "0",
            "msg1": "정상처리",
        }

        if output:
            data["output"] = output

        return MockResponseFactory.success(data)

    @staticmethod
    def error(
        status_code: int = 400,
        error_code: str = "ERROR",
        message: str = "Bad Request",
    ) -> MagicMock:
        """Create a mock error response.

        Args:
            status_code: HTTP status code (default: 400)
            error_code: KIS error code (default: "ERROR")
            message: Error message (default: "Bad Request")

        Returns:
            Mock httpx.Response that raises HTTPStatusError
        """
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = status_code
        mock_response.json.return_value = {
            "rt_cd": "-1",
            "msg_cd": error_code,
            "msg1": message,
        }

        # Create HTTPStatusError
        http_error = httpx.HTTPStatusError(
            f"{status_code} {message}",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.raise_for_status.side_effect = http_error
        mock_response.reason_phrase = message
        mock_response.text = message

        return mock_response

    @staticmethod
    def kis_error(
        error_code: str = "EGW00223",
        message: str = "Invalid parameter",
    ) -> MagicMock:
        """Create a mock KIS API error response (HTTP 200 with error in body).

        KIS API sometimes returns HTTP 200 with rt_cd="-1" for errors.

        Args:
            error_code: KIS error code
            message: Error message

        Returns:
            Mock response with KIS error structure
        """
        data = {
            "rt_cd": "-1",
            "msg_cd": error_code,
            "msg1": message,
        }

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = data
        mock_response.raise_for_status = MagicMock()
        mock_response.reason_phrase = "OK"
        mock_response.text = str(data)

        return mock_response

    @staticmethod
    def rate_limit() -> MagicMock:
        """Create a mock rate limit response (HTTP 429).

        Returns:
            Mock response with 429 status code
        """
        return MockResponseFactory.error(
            status_code=429,
            error_code="EGW00108",
            message="Exceeds the daily request limit",
        )

    @staticmethod
    def unauthorized() -> MagicMock:
        """Create a mock unauthorized response (HTTP 401).

        Returns:
            Mock response with 401 status code
        """
        return MockResponseFactory.error(
            status_code=401,
            error_code="EGW00001",
            message="Authentication failed",
        )

    @staticmethod
    def server_error(message: str = "Internal Server Error") -> MagicMock:
        """Create a mock server error response (HTTP 500).

        Args:
            message: Error message

        Returns:
            Mock response with 500 status code
        """
        return MockResponseFactory.error(
            status_code=500,
            error_code="EGW50000",
            message=message,
        )

    @staticmethod
    def oauth_token_response(
        access_token: str = "test_token",
        expires_in: int = 86400,
        token_type: str = "Bearer",
    ) -> MagicMock:
        """Create a mock OAuth token response.

        Args:
            access_token: Access token string
            expires_in: Token lifetime in seconds
            token_type: Token type

        Returns:
            Mock OAuth token response
        """
        data = {
            "access_token": access_token,
            "token_type": token_type,
            "expires_in": expires_in,
            "token_type_bearer": token_type,
        }

        return MockResponseFactory.success(data)


# Convenience functions for backward compatibility


def mock_success(data: dict[str, Any] | None = None) -> MagicMock:
    """Create a mock success response."""
    return MockResponseFactory.success(data)


def mock_kis_success(output: dict[str, Any] | None = None) -> MagicMock:
    """Create a mock KIS API success response."""
    return MockResponseFactory.success_kis(output)


def mock_error(
    status_code: int = 400,
    error_code: str = "ERROR",
    message: str = "Bad Request",
) -> MagicMock:
    """Create a mock error response."""
    return MockResponseFactory.error(status_code, error_code, message)


def mock_kis_error(
    error_code: str = "EGW00223",
    message: str = "Invalid parameter",
) -> MagicMock:
    """Create a mock KIS API error response."""
    return MockResponseFactory.kis_error(error_code, message)


def mock_rate_limit() -> MagicMock:
    """Create a mock rate limit response."""
    return MockResponseFactory.rate_limit()


def mock_oauth_token(
    access_token: str = "test_token",
    expires_in: int = 86400,
) -> MagicMock:
    """Create a mock OAuth token response."""
    return MockResponseFactory.oauth_token_response(access_token, expires_in)
