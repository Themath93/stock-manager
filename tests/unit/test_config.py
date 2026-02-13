"""Tests for KISConfig and related configuration classes.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

import os
from unittest.mock import patch

import pytest

from stock_manager.adapters.broker.kis.config import (
    KISAccessToken,
    KISConfig,
    KISConnectionState,
    KIS_API_BASE_URL,
    KIS_API_BASE_URL_REAL,
    KIS_OAUTH_PATH,
    KIS_OAUTH_PATH_REAL,
)


class TestKISConfig:
    """Tests for KISConfig."""

    def test_config_loads_from_env(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test configuration loads from environment variables."""
        with patch.dict(os.environ, mock_env_vars, clear=True):
            config = KISConfig(_env_file=None)

            assert config.app_key.get_secret_value() == "test_app_key_12345"
            assert config.app_secret.get_secret_value() == "test_app_secret_67890"
            assert config.account_number == "12345678"
            assert config.account_product_code == "01"
            assert config.request_retry_enabled is True
            assert config.request_max_attempts == 3
            assert config.request_initial_backoff_ms == 1
            assert config.request_backoff_multiplier == 1.0
            assert config.auto_reauth_enabled is True

    def test_config_defaults_to_mock_trading(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test default to mock trading environment."""
        env = mock_env_vars.copy()
        env.pop("KIS_USE_MOCK", None)

        with patch.dict(os.environ, env, clear=True):
            config = KISConfig(_env_file=None)

            assert config.use_mock is True
            assert config.is_mock_trading is True

    def test_config_use_mock_false(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test setting use_mock to False."""
        env = mock_env_vars.copy()
        env["KIS_USE_MOCK"] = "false"

        with patch.dict(os.environ, env, clear=True):
            config = KISConfig(_env_file=None)

            assert config.use_mock is False
            assert config.is_mock_trading is False

    def test_api_base_url_mock(self, kis_config: KISConfig) -> None:
        """Test API base URL for mock trading."""
        assert kis_config.api_base_url == KIS_API_BASE_URL
        assert "29443" in kis_config.api_base_url

    def test_api_base_url_real(self, kis_config_real: KISConfig) -> None:
        """Test API base URL for real trading."""
        assert kis_config_real.api_base_url == KIS_API_BASE_URL_REAL
        assert "9443" in kis_config_real.api_base_url

    def test_oauth_path_mock(self, kis_config: KISConfig) -> None:
        """Test OAuth path for mock trading."""
        assert kis_config.oauth_path == KIS_OAUTH_PATH
        assert kis_config.oauth_path.endswith("tokenP")

    def test_oauth_path_real(self, kis_config_real: KISConfig) -> None:
        """Test OAuth path for real trading."""
        assert kis_config_real.oauth_path == KIS_OAUTH_PATH_REAL
        assert kis_config_real.oauth_path.endswith("tokenP")

    def test_get_canonical_account_number_with_account(
        self,
        kis_config: KISConfig,
    ) -> None:
        """Test canonical account number formatting with account."""
        kis_config.account_number = "12345678"
        kis_config.account_product_code = "01"

        result = kis_config.get_canonical_account_number()

        assert result == "12345678-01"

    def test_get_canonical_account_number_without_account(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test canonical account number without account returns None."""
        env = mock_env_vars.copy()
        env.pop("KIS_ACCOUNT_NUMBER", None)

        with patch.dict(os.environ, env, clear=True):
            config = KISConfig(_env_file=None)

            result = config.get_canonical_account_number()

            assert result is None

    def test_config_validation_missing_app_key(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test validation fails when APP_KEY is missing."""
        env = mock_env_vars.copy()
        env["KIS_APP_KEY"] = ""

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="KIS_APP_KEY is required"):
                KISConfig(_env_file=None)

    def test_config_validation_missing_app_secret(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test validation fails when APP_SECRET is missing."""
        env = mock_env_vars.copy()
        env["KIS_APP_SECRET"] = ""

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="KIS_APP_SECRET is required"):
                KISConfig(_env_file=None)

    def test_config_ignores_unknown_env_vars(
        self,
        mock_env_vars: dict,
    ) -> None:
        """Test unknown environment variables are ignored."""
        env = mock_env_vars.copy()
        env["KIS_UNKNOWN_VAR"] = "should_be_ignored"

        with patch.dict(os.environ, env, clear=True):
            # Should not raise error for unknown vars
            config = KISConfig(_env_file=None)

            assert config is not None


class TestKISAccessToken:
    """Tests for KISAccessToken."""

    def test_token_initialization(self) -> None:
        """Test token initialization with all fields."""
        token = KISAccessToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
        )

        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

    def test_token_defaults(self) -> None:
        """Test token default values."""
        token = KISAccessToken(access_token="test_token")

        assert token.token_type == "Bearer"
        assert token.expires_in == 86400  # 24 hours
        assert token.token_type_bearer == "Bearer"

    def test_authorization_header(self) -> None:
        """Test authorization header formatting."""
        token = KISAccessToken(access_token="my_token")

        header = token.authorization_header

        assert header == "Bearer my_token"

    def test_is_valid_with_valid_token(self) -> None:
        """Test is_valid returns True for valid token."""
        token = KISAccessToken(access_token="valid_token")

        assert token.is_valid() is True

    def test_is_valid_with_empty_token(self) -> None:
        """Test is_valid returns False for empty token."""
        token = KISAccessToken(access_token="")

        assert token.is_valid() is False

    def test_is_valid_with_whitespace_token(self) -> None:
        """Test is_valid returns False for whitespace-only token."""
        token = KISAccessToken(access_token="   ")

        assert token.is_valid() is False

    def test_is_valid_with_none_token(self) -> None:
        """Test is_valid handles None token."""
        # Can't create KISAccessToken with None, but test for empty string
        token = KISAccessToken(access_token="")

        assert token.is_valid() is False


class TestKISConnectionState:
    """Tests for KISConnectionState."""

    def test_state_initialization(self, kis_config: KISConfig) -> None:
        """Test state initialization with config."""
        state = KISConnectionState(config=kis_config)

        assert state.config is kis_config
        assert state.access_token is None
        assert state.is_authenticated is False

    def test_update_token(self, kis_config: KISConfig) -> None:
        """Test updating access token."""
        state = KISConnectionState(config=kis_config)
        token = KISAccessToken(access_token="new_token")

        state.update_token(token)

        assert state.access_token is token
        assert state.is_authenticated is True

    def test_update_token_with_invalid_token(
        self,
        kis_config: KISConfig,
    ) -> None:
        """Test updating with invalid token marks as not authenticated."""
        state = KISConnectionState(config=kis_config)
        token = KISAccessToken(access_token="")

        state.update_token(token)

        assert state.access_token is token
        assert state.is_authenticated is False

    def test_clear_token(self, kis_config: KISConfig) -> None:
        """Test clearing access token."""
        state = KISConnectionState(config=kis_config)
        token = KISAccessToken(access_token="test_token")

        state.update_token(token)
        assert state.is_authenticated is True

        state.clear_token()

        assert state.access_token is None
        assert state.is_authenticated is False


class TestKISConfigConstants:
    """Tests for KIS API configuration constants."""

    def test_api_base_urls(self) -> None:
        """Test API base URL constants."""
        assert KIS_API_BASE_URL.startswith("https://")
        assert "29443" in KIS_API_BASE_URL  # Mock port
        assert KIS_API_BASE_URL_REAL.startswith("https://")
        assert "9443" in KIS_API_BASE_URL_REAL  # Real port

    def test_oauth_paths(self) -> None:
        """Test OAuth path constants."""
        assert KIS_OAUTH_PATH.startswith("/")
        assert KIS_OAUTH_PATH.endswith("tokenP")
        assert KIS_OAUTH_PATH_REAL.startswith("/")
        assert KIS_OAUTH_PATH_REAL.endswith("tokenP")

    def test_mock_vs_real_urls_differ(self) -> None:
        """Test mock and real URLs are different."""
        assert KIS_API_BASE_URL != KIS_API_BASE_URL_REAL
        # Personal OAuth path is the same; only domain differs.
        assert KIS_OAUTH_PATH == KIS_OAUTH_PATH_REAL
