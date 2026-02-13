"""KIS (Korea Investment Securities) REST API client.

This module provides the base REST client for interacting with the KIS API,
including authentication, request handling, and response processing.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from stock_manager.adapters.broker.kis.config import (
    KISAccessToken,
    KISConfig,
    KISConnectionState,
)
from stock_manager.adapters.broker.kis.token_cache import load_cached_token, save_cached_token
from stock_manager.adapters.broker.kis.exceptions import (
    KISAPIError,
    KISAuthenticationError,
    KISRateLimitError,
)

logger = logging.getLogger(__name__)


class KISRestClient:
    """Base REST client for KIS API.

    This client handles HTTP communication with the KIS (Korea Investment Securities)
    API, including authentication token management, request signing, and error handling.

    The client uses synchronous operations with httpx.

    Attributes:
        config: KIS configuration instance
        state: Current connection state including access token
        timeout: Default request timeout in seconds

    Example:
        >>> config = KISConfig()
        >>> client = KISRestClient(config)
        >>> client.authenticate()
        >>> response = client.make_request("GET", "/uapi/domestic-stock/v1/quotations/inquire-price")
    """

    # API version header
    API_VERSION = "1.0"

    def __init__(
        self,
        config: KISConfig,
        *,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize KIS REST client.

        Args:
            config: KIS configuration instance
            timeout: Default request timeout in seconds (default: 30.0)
            client: Optional custom httpx.Client for testing/advanced use

        Raises:
            KISConfigurationError: If configuration is invalid
        """
        self.config = config
        self.state = KISConnectionState(config=config)
        self.timeout = timeout

        # HTTP client setup
        if client is not None:
            self._http_client = client
        else:
            self._http_client = httpx.Client(
                base_url=config.api_base_url,
                timeout=timeout,
                headers=self._get_default_headers(),
            )

    def _get_default_headers(self) -> dict[str, str]:
        """Get default HTTP headers for all requests.

        Returns:
            Dictionary of default headers
        """
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "stock-manager/0.1.0",
        }

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dictionary of authentication headers

        Raises:
            KISAuthenticationError: If not authenticated or token is invalid
        """
        if not self.state.is_authenticated or self.state.access_token is None:
            raise KISAuthenticationError("Client is not authenticated. Call authenticate() first.")

        return {
            "Authorization": self.state.access_token.authorization_header,
            "appkey": self.config.app_key.get_secret_value(),
            "appsecret": self.config.app_secret.get_secret_value(),
        }

    def authenticate(self) -> KISAccessToken:
        """Authenticate with KIS API and obtain access token.

        Makes a POST request to the OAuth token endpoint to retrieve an
        access token for authenticated API requests.

        Returns:
            KISAccessToken instance containing the access token

        Raises:
            KISAuthenticationError: If authentication fails
            KISAPIError: If the API request fails

        Example:
            >>> client = KISRestClient(config)
            >>> token = client.authenticate()
            >>> print(token.access_token)
        """
        # Fast-path: reuse in-memory token if still valid.
        now = datetime.now(timezone.utc)
        if self.state.is_authenticated and self.state.access_token is not None:
            # If we don't know expiry, assume valid to avoid unnecessary re-issuance.
            if self.state.access_token_expires_at is None:
                return self.state.access_token
            if self.state.access_token_expires_at > now + timedelta(seconds=60):
                return self.state.access_token

        # Disk cache: reuse token across processes/restarts (avoids KIS OAuth rate limits).
        if self.config.token_cache_enabled:
            cached = load_cached_token(
                self.config.get_token_cache_path(),
                app_key=self.config.app_key.get_secret_value(),
                api_base_url=self.config.api_base_url,
                oauth_path=self.config.oauth_path,
            )
            if cached is not None:
                self.state.update_token(cached.token)
                self.state.access_token_expires_at = cached.expires_at
                return cached.token

        url = self.config.oauth_path
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.config.app_key.get_secret_value(),
            "appsecret": self.config.app_secret.get_secret_value(),
            "custtype": self.config.custtype,
        }

        payload = {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key.get_secret_value(),
            "appsecret": self.config.app_secret.get_secret_value(),
        }

        try:
            response = self._http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Handle KIS API response structure
            # The response may have different structures depending on the endpoint
            if "access_token" not in data:
                raise KISAuthenticationError("Invalid token response: missing access_token")

            token = KISAccessToken(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 86400),
                token_type_bearer=data.get("token_type_bearer", "Bearer"),
            )

            self.state.update_token(token)
            # KIS returns expires_in in seconds (typically 86400).
            expires_in = int(data.get("expires_in", 86400))
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            self.state.access_token_expires_at = expires_at

            if self.config.token_cache_enabled:
                try:
                    save_cached_token(
                        self.config.get_token_cache_path(),
                        token=token,
                        expires_at=expires_at,
                        app_key=self.config.app_key.get_secret_value(),
                        api_base_url=self.config.api_base_url,
                        oauth_path=self.config.oauth_path,
                        access_token_token_expired=data.get("access_token_token_expired"),
                    )
                except Exception:
                    # Cache is best-effort; never fail auth because we couldn't write.
                    pass
            logger.info("Successfully authenticated with KIS API")

            return token

        except httpx.HTTPStatusError as e:
            # KIS often returns useful error details in JSON body.
            details = ""
            try:
                data = e.response.json()
                parts = []
                for k in ["rt_cd", "msg_cd", "msg1", "error", "error_description"]:
                    if k in data and data.get(k) not in (None, ""):
                        parts.append(f"{k}={data.get(k)}")
                if parts:
                    details = " (" + ", ".join(parts) + ")"
            except Exception:
                pass
            raise KISAuthenticationError(
                f"Authentication failed: {e.response.status_code}{details}",
                error_code=str(e.response.status_code),
            ) from e
        except httpx.RequestError as e:
            raise KISAPIError(f"Network error during authentication: {e}") from e

    def make_request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> dict[str, Any]:
        """Make an authenticated API request to KIS API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path (e.g., "/uapi/domestic-stock/v1/quotations/inquire-price")
            params: URL query parameters
            json_data: JSON request body for POST/PUT requests
            headers: Additional HTTP headers (merged with auth headers)
            require_auth: Whether to include authentication headers (default: True)

        Returns:
            Parsed JSON response data

        Raises:
            KISAuthenticationError: If authentication is required but not available
            KISAPIError: If the API request fails
            KISRateLimitError: If rate limit is exceeded

        Example:
            >>> response = client.make_request(
            ...     "GET",
            ...     "/uapi/domestic-stock/v1/quotations/inquire-price",
            ...     params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"}
            ... )
            >>> print(response["output"])
        """
        max_attempts = max(1, self.config.request_max_attempts) if self.config.request_retry_enabled else 1
        reauth_attempted = False

        for attempt in range(1, max_attempts + 1):
            # Prepare headers per-attempt to include refreshed token after reauth.
            request_headers = self._get_default_headers()
            if require_auth:
                auth_headers = self._get_auth_headers()
                request_headers.update(auth_headers)
            if headers:
                request_headers.update(headers)

            # Add personal account header if available
            if self.config.account_number:
                request_headers["hashkey"] = self.config.account_number

            try:
                response = self._http_client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                )

                if response.status_code in (401, 403):
                    if (
                        require_auth
                        and self.config.auto_reauth_enabled
                        and not reauth_attempted
                    ):
                        reauth_attempted = True
                        self.authenticate()
                        continue

                if response.status_code == 429:
                    raise KISRateLimitError(
                        "API rate limit exceeded. Please retry later.",
                        status_code=429,
                    )

                response.raise_for_status()
                data = response.json()

                if self._is_error_response(data):
                    if (
                        require_auth
                        and self.config.auto_reauth_enabled
                        and not reauth_attempted
                        and self._is_auth_error_response(data)
                    ):
                        reauth_attempted = True
                        self.authenticate()
                        continue
                    raise self._create_api_error_from_response(data)

                return data

            except KISRateLimitError:
                if self._should_retry_status(429, attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue
                raise
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                if (
                    status_code in (401, 403)
                    and require_auth
                    and self.config.auto_reauth_enabled
                    and not reauth_attempted
                ):
                    reauth_attempted = True
                    self.authenticate()
                    continue

                if self._should_retry_status(status_code, attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue

                error_data = None
                try:
                    error_data = e.response.json()
                except Exception:
                    pass

                raise KISAPIError(
                    f"API request failed: {e.response.status_code} {e.response.reason_phrase}",
                    status_code=e.response.status_code,
                    response_data=error_data,
                ) from e
            except httpx.RequestError as e:
                if self._should_retry_network(attempt, max_attempts):
                    self._sleep_before_retry(attempt)
                    continue
                raise KISAPIError(f"Network error during API request: {e}") from e

        raise KISAPIError("API request failed after maximum retry attempts")

    def _is_error_response(self, data: dict[str, Any]) -> bool:
        """Check if API response contains an error.

        KIS API may return HTTP 200 with error codes in response body.

        Args:
            data: Parsed JSON response data

        Returns:
            True if response contains an error, False otherwise
        """
        # KIS API error response structure varies by endpoint.
        # In practice, `rt_cd` is the most reliable indicator:
        # - "0" success
        # - "-1"/"1" error
        rt_cd = data.get("rt_cd")

        has_error_code = data.get("error_code") is not None
        has_error = data.get("error") is not None

        if rt_cd is not None:
            return str(rt_cd) != "0"

        return bool(has_error_code or has_error or data.get("error_description") is not None)

    def _create_api_error_from_response(self, data: dict[str, Any]) -> KISAPIError:
        """Create KISAPIError from error response data.

        Args:
            data: Parsed JSON response containing error information

        Returns:
            KISAPIError instance with details from response
        """
        error_code = (
            data.get("msg_cd") or data.get("error_code") or data.get("rt_cd") or "UNKNOWN"
        )
        error_message = (
            data.get("msg1") or data.get("error_message") or data.get("message") or "Unknown error"
        )

        return KISAPIError(
            message=error_message,
            error_code=error_code,
            response_data=data,
        )

    def _is_auth_error_response(self, data: dict[str, Any]) -> bool:
        """Best-effort check for authentication error payloads."""
        msg = " ".join(
            str(data.get(key, ""))
            for key in ("msg1", "error", "error_description", "message")
        ).lower()
        return any(keyword in msg for keyword in ("token", "auth", "인증"))

    def _should_retry_status(self, status_code: int, attempt: int, max_attempts: int) -> bool:
        if not self.config.request_retry_enabled:
            return False
        if attempt >= max_attempts:
            return False
        return status_code == 429 or 500 <= status_code <= 599

    def _should_retry_network(self, attempt: int, max_attempts: int) -> bool:
        return self.config.request_retry_enabled and attempt < max_attempts

    def _sleep_before_retry(self, attempt: int) -> None:
        base = max(1, self.config.request_initial_backoff_ms) / 1000.0
        multiplier = max(1.0, self.config.request_backoff_multiplier)
        delay = base * (multiplier ** max(0, attempt - 1))
        time.sleep(delay)

    def close(self) -> None:
        """Close the HTTP client and release resources.

        Example:
            >>> client = KISRestClient(config)
            >>> client.authenticate()
            >>> # ... use client ...
            >>> client.close()
        """
        self._http_client.close()

    def __enter__(self) -> "KISRestClient":
        """Context manager entry.

        Returns:
            Self for use in with statement
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit.

        Closes the HTTP client when exiting the context.
        """
        self.close()

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.state.is_authenticated

    def get_access_token(self) -> KISAccessToken | None:
        """Get the current access token.

        Returns:
            Current KISAccessToken or None if not authenticated
        """
        return self.state.access_token
