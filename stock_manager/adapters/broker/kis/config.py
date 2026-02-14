"""KIS (Korea Investment Securities) API configuration management.

This module provides configuration classes for managing KIS API credentials,
tokens, and connection settings.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import PrivateAttr, SecretStr
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
        KIS_APP_KEY: Real trading application key issued by KIS
        KIS_APP_SECRET: Real trading application secret key issued by KIS
        KIS_MOCK_APP_KEY: Mock trading application key (optional, preferred in mock mode)
        KIS_MOCK_SECRET: Mock trading application secret (optional, preferred in mock mode)
        KIS_ACCOUNT_NUMBER: Real trading account number (optional)
        KIS_MOCK_ACCOUNT_NUMBER: Mock trading account number (optional, preferred in mock mode)
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
    app_key: SecretStr | None = None
    app_secret: SecretStr | None = None
    mock_app_key: SecretStr | None = None
    mock_secret: SecretStr | None = None

    # Account information (optional for token generation)
    account_number: str | None = None
    mock_account_number: str | None = None
    account_product_code: str = "01"

    # Environment settings
    use_mock: bool = True
    # Customer type header used by OAuth and some APIs: P=individual, B=corporate
    custtype: Literal["P", "B"] = "P"
    # Token caching (strongly recommended to avoid KIS OAuth rate limits)
    token_cache_enabled: bool = True
    token_cache_path: str | None = None
    # Request stabilization controls
    request_retry_enabled: bool = True
    request_max_attempts: int = 3
    request_initial_backoff_ms: int = 200
    request_backoff_multiplier: float = 2.0
    auto_reauth_enabled: bool = True

    _effective_app_key: SecretStr = PrivateAttr(default=SecretStr(""))
    _effective_app_secret: SecretStr = PrivateAttr(default=SecretStr(""))
    _effective_account_number: str | None = PrivateAttr(default=None)
    _credential_source: Literal["real", "mock", "real_fallback"] = PrivateAttr(default="real")
    _account_source: Literal["real", "mock", "real_fallback", "none"] = PrivateAttr(default="none")
    _fallback_warnings: list[str] = PrivateAttr(default_factory=list)

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

    @property
    def effective_app_key(self) -> SecretStr:
        """Effective app key selected by current mode/fallback policy."""
        return self._effective_app_key

    @property
    def effective_app_secret(self) -> SecretStr:
        """Effective app secret selected by current mode/fallback policy."""
        return self._effective_app_secret

    @property
    def effective_account_number(self) -> str | None:
        """Effective account number selected by current mode/fallback policy."""
        return self._effective_account_number

    @property
    def fallback_warnings(self) -> tuple[str, ...]:
        """Warnings emitted when mock mode falls back to real credentials/account."""
        return tuple(self._fallback_warnings)

    @property
    def is_using_fallback_credentials(self) -> bool:
        """True when mock mode is using real credentials as fallback."""
        return self._credential_source == "real_fallback"

    @property
    def is_using_fallback_account(self) -> bool:
        """True when mock mode is using real account as fallback."""
        return self._account_source == "real_fallback"

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
        real_key = self._secret_value(self.app_key)
        real_secret = self._secret_value(self.app_secret)
        mock_key = self._secret_value(self.mock_app_key)
        mock_secret = self._secret_value(self.mock_secret)
        real_account = self._normalized_or_none(self.account_number)
        mock_account = self._normalized_or_none(self.mock_account_number)

        self._fallback_warnings.clear()

        if self.use_mock:
            selected_key, selected_secret, credential_source = self._resolve_mock_credentials(
                mock_key=mock_key,
                mock_secret=mock_secret,
                real_key=real_key,
                real_secret=real_secret,
            )
            selected_account, account_source = self._resolve_mock_account(
                mock_account=mock_account,
                real_account=real_account,
            )
        else:
            if not real_key:
                raise ValueError("KIS_USE_MOCK=false requires KIS_APP_KEY.")
            if not real_secret:
                raise ValueError("KIS_USE_MOCK=false requires KIS_APP_SECRET.")
            selected_key = real_key
            selected_secret = real_secret
            selected_account = real_account
            credential_source = "real"
            account_source = "real" if real_account else "none"

        self._effective_app_key = SecretStr(selected_key)
        self._effective_app_secret = SecretStr(selected_secret)
        self._effective_account_number = selected_account
        self._credential_source = credential_source
        self._account_source = account_source

        # Backward-compat: existing call sites read app_key/app_secret/account_number directly.
        self.app_key = self._effective_app_key
        self.app_secret = self._effective_app_secret
        self.account_number = self._effective_account_number

    @staticmethod
    def _secret_value(value: SecretStr | None) -> str:
        if value is None:
            return ""
        return value.get_secret_value().strip()

    @staticmethod
    def _normalized_or_none(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _resolve_mock_credentials(
        self,
        *,
        mock_key: str,
        mock_secret: str,
        real_key: str,
        real_secret: str,
    ) -> tuple[str, str, Literal["mock", "real_fallback"]]:
        if mock_key and mock_secret:
            return mock_key, mock_secret, "mock"

        raise ValueError(
            "KIS_USE_MOCK=true requires KIS_MOCK_APP_KEY and KIS_MOCK_SECRET. "
            "Refusing to use KIS_APP_KEY/KIS_APP_SECRET in mock mode. "
            "Fix: set KIS_MOCK_APP_KEY/KIS_MOCK_SECRET or set KIS_USE_MOCK=false."
        )

    def _resolve_mock_account(
        self,
        *,
        mock_account: str | None,
        real_account: str | None,
    ) -> tuple[str | None, Literal["mock", "real_fallback", "none"]]:
        if mock_account:
            return mock_account, "mock"

        raise ValueError(
            "KIS_USE_MOCK=true requires KIS_MOCK_ACCOUNT_NUMBER. "
            "Refusing to use KIS_ACCOUNT_NUMBER in mock mode because KIS mock APIs commonly fail with "
            "OPSQ2000 ERROR : INPUT INVALID_CHECK_ACNO when a real account is used. "
            "Fix: set KIS_MOCK_ACCOUNT_NUMBER (8 digits) or set KIS_USE_MOCK=false."
        )


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
