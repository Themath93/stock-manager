"""KIS (Korea Investment Securities) API configuration management.

This module provides configuration classes for managing KIS API credentials,
tokens, and connection settings.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from stock_manager.config.paths import default_env_file


# API endpoints
KIS_API_BASE_URL: Final = "https://openapivts.koreainvestment.com:29443"  # Mock trading
KIS_API_BASE_URL_REAL: Final = "https://openapi.koreainvestment.com:9443"  # Real trading
KIS_OAUTH_PATH: Final = "/oauth2/tokenP"
# KIS personal accounts use /oauth2/tokenP for both mock and real.
# (Some legacy/partner flows use /oauth2/token, but that's out of scope here.)
KIS_OAUTH_PATH_REAL: Final = "/oauth2/tokenP"


class KISConfig(BaseSettings):
    """KIS API configuration settings.

    This class manages configuration for the KIS (Korea Investment Securities) API,
    including application credentials, account information, and API endpoints.

    The configuration is loaded from environment variables with the "KIS_" prefix.

    Environment Variables:
        KIS_APP_KEY: Application key issued by KIS
        KIS_APP_SECRET: Application secret key issued by KIS
        KIS_ACCOUNT_NUMBER: Trading account number (optional)
        KIS_ACCOUNT_PRODUCT_CODE: Account product code (optional, default: "01")
        KIS_USE_MOCK: Use mock trading environment (optional, default: true)

    Example:
        >>> config = KISConfig()
        >>> print(config.app_key.get_secret_value())
        >>> print(config.is_mock_trading)
    """

    _DEFAULT_ENV_FILE = str(default_env_file())
    model_config = SettingsConfigDict(
        env_prefix="KIS_",
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Authentication credentials
    app_key: SecretStr
    app_secret: SecretStr

    # Account information (optional for token generation)
    account_number: str | None = None
    account_product_code: str = "01"

    # Environment settings
    use_mock: bool = True
    # Customer type header used by OAuth and some APIs: P=individual, B=corporate
    custtype: Literal["P", "B"] = "P"
    # Token caching (strongly recommended to avoid KIS OAuth rate limits)
    token_cache_enabled: bool = True
    token_cache_path: str | None = None

    def get_token_cache_path(self) -> Path:
        """Return the access token cache file path.

        Defaults to ~/.stock_manager/kis_token_{real|paper}.json, but can be overridden
        via KIS_TOKEN_CACHE_PATH.
        """
        if self.token_cache_path:
            return Path(self.token_cache_path).expanduser()
        mode = "paper" if self.use_mock else "real"
        return Path.home() / ".stock_manager" / f"kis_token_{mode}.json"

    @property
    def api_base_url(self) -> str:
        """Get the API base URL based on environment setting.

        Returns:
            Mock trading URL if use_mock is True, otherwise real trading URL
        """
        return KIS_API_BASE_URL if self.use_mock else KIS_API_BASE_URL_REAL

    @property
    def oauth_path(self) -> str:
        """Get the OAuth token endpoint path.

        Returns:
            Mock trading OAuth path if use_mock is True, otherwise real trading path
        """
        return KIS_OAUTH_PATH if self.use_mock else KIS_OAUTH_PATH_REAL

    @property
    def is_mock_trading(self) -> bool:
        """Check if using mock trading environment.

        Returns:
            True if using mock trading, False for real trading
        """
        return self.use_mock

    def get_canonical_account_number(self) -> str | None:
        """Get the canonical account number format.

        Combines account_number and account_product_code in the format
        required by KIS API.

        Returns:
            Formatted account number (e.g., "12345678-01") or None if not configured

        Example:
            >>> config = KISConfig()
            >>> config.account_number = "12345678"
            >>> config.account_product_code = "01"
            >>> config.get_canonical_account_number()
            '12345678-01'
        """
        if not self.account_number:
            return None
        return f"{self.account_number}-{self.account_product_code}"

    def model_post_init(self, __context: object) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If required credentials are missing
        """
        if not self.app_key.get_secret_value():
            raise ValueError("KIS_APP_KEY is required")
        if not self.app_secret.get_secret_value():
            raise ValueError("KIS_APP_SECRET is required")


@dataclass(frozen=True)
class KISAccessToken:
    """KIS API access token.

    This dataclass represents an OAuth access token issued by the KIS API,
    including the token string, type, and expiration information.

    Attributes:
        access_token: The OAuth access token string
        token_type: Token type (typically "Bearer")
        expires_in: Token lifetime in seconds (default: 86400 = 24 hours)
        token_type_bearer: Token type field from KIS API (always "Bearer")

    Example:
        >>> token = KISAccessToken(
        ...     access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ...     token_type="Bearer",
        ...     expires_in=86400
        ... )
        >>> print(token.is_valid())
        True
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24 hours in seconds
    token_type_bearer: str = "Bearer"

    @property
    def authorization_header(self) -> str:
        """Get the formatted authorization header value.

        Returns:
            Authorization header value (e.g., "Bearer eyJhbG...")

        Example:
            >>> token = KISAccessToken(access_token="token123")
            >>> token.authorization_header
            'Bearer token123'
        """
        return f"{self.token_type} {self.access_token}"

    def is_valid(self) -> bool:
        """Check if the access token is valid.

        A token is considered valid if it has a non-empty access_token string.

        Returns:
            True if token is valid, False otherwise
        """
        return bool(self.access_token and self.access_token.strip())


@dataclass
class KISConnectionState:
    """KIS API connection state.

    This dataclass maintains the current state of the KIS API connection,
    including the current access token and configuration.

    Attributes:
        config: KIS configuration instance
        access_token: Current access token (None if not authenticated)
        is_authenticated: Whether client is authenticated

    Example:
        >>> config = KISConfig()
        >>> state = KISConnectionState(config=config)
        >>> print(state.is_authenticated)
        False
        >>> state.access_token = KISAccessToken(access_token="token123")
        >>> state.is_authenticated = True
    """

    config: KISConfig
    access_token: KISAccessToken | None = None
    access_token_expires_at: datetime | None = None
    is_authenticated: bool = False

    def __post_init__(self) -> None:
        """Ensure is_authenticated is set correctly on initialization."""
        # Force is_authenticated to False on init
        object.__setattr__(self, "is_authenticated", False)

    def update_token(self, token: KISAccessToken) -> None:
        """Update the access token and mark as authenticated.

        Args:
            token: New access token to set

        Example:
            >>> state = KISConnectionState(config=config)
            >>> new_token = KISAccessToken(access_token="new_token")
            >>> state.update_token(new_token)
            >>> print(state.is_authenticated)
            True
        """
        self.access_token = token
        self.is_authenticated = token.is_valid()
        # Expires-at is managed by the caller (client.authenticate) because KISAccessToken
        # doesn't carry a timestamp and may be set from an external source (tests, setup).

    def clear_token(self) -> None:
        """Clear the access token and mark as not authenticated.

        Example:
            >>> state = KISConnectionState(config=config)
            >>> state.update_token(KISAccessToken(access_token="token"))
            >>> state.clear_token()
            >>> print(state.is_authenticated)
            False
        """
        self.access_token = None
        self.is_authenticated = False
