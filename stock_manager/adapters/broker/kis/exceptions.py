"""KIS (Korea Investment Securities) API custom exceptions.

This module defines custom exceptions for handling KIS API-specific errors.
"""


class KISException(Exception):
    """Base exception for KIS API errors.

    All KIS-specific exceptions inherit from this base class.
    """

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        """Initialize KIS exception.

        Args:
            message: Human-readable error message
            error_code: Optional KIS API error code
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class KISConfigurationError(KISException):
    """Exception raised for configuration-related errors.

    This includes missing or invalid configuration values such as:
    - Missing API key or secret
    - Invalid environment configuration
    - Missing required settings
    """

    pass


class KISAuthenticationError(KISException):
    """Exception raised for authentication failures.

    This includes:
    - Invalid credentials
    - Token generation failures
    - Token expiration
    - Authorization failures
    """

    pass


class KISAPIError(KISException):
    """Exception raised for KIS API request/response errors.

    This includes:
    - HTTP errors (4xx, 5xx)
    - API response format errors
    - Rate limiting errors
    - Network connectivity issues
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        response_data: dict | None = None,
    ) -> None:
        """Initialize KIS API error.

        Args:
            message: Human-readable error message
            error_code: Optional KIS API error code from response
            status_code: HTTP status code
            response_data: Full API response data for debugging
        """
        super().__init__(message, error_code=error_code)
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        """Return string representation of the API error."""
        parts = []
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        parts.append(self.message)
        return " ".join(parts)


class KISRateLimitError(KISAPIError):
    """Exception raised when API rate limit is exceeded.

    The KIS API has rate limits on requests. This exception is raised
    when those limits are exceeded.
    """

    pass


class KISValidationError(KISException):
    """Exception raised for input validation errors.

    This includes:
    - Invalid request parameters
    - Missing required fields
    - Invalid data formats
    """

    pass
