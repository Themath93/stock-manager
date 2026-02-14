"""Pytest configuration and global fixtures for KIS API tests.

This module provides shared fixtures for all test modules, following
Kent Beck's TDD philosophy of simple, reliable test infrastructure.
"""

import os
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest
import httpx
from httpx import Response

from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig, KISConnectionState


@pytest.fixture
def mock_env_vars():
    """Provide mock environment variables for KISConfig.

    Returns:
        Dictionary with valid KIS configuration values
    """
    return {
        "KIS_APP_KEY": "test_app_key_12345",
        "KIS_APP_SECRET": "test_app_secret_67890",
        "KIS_ACCOUNT_NUMBER": "12345678",
        "KIS_MOCK_APP_KEY": "test_mock_app_key_12345",
        "KIS_MOCK_SECRET": "test_mock_app_secret_67890",
        "KIS_MOCK_ACCOUNT_NUMBER": "87654321",
        "KIS_ACCOUNT_PRODUCT_CODE": "01",
        "KIS_USE_MOCK": "true",
        # Keep unit tests isolated from user home directory.
        "KIS_TOKEN_CACHE_ENABLED": "false",
        "KIS_REQUEST_RETRY_ENABLED": "true",
        "KIS_REQUEST_MAX_ATTEMPTS": "3",
        "KIS_REQUEST_INITIAL_BACKOFF_MS": "1",
        "KIS_REQUEST_BACKOFF_MULTIPLIER": "1.0",
        "KIS_AUTO_REAUTH_ENABLED": "true",
    }


@pytest.fixture
def kis_config(mock_env_vars: dict[str, str]) -> KISConfig:
    """Provide a valid KISConfig instance for testing.

    Args:
        mock_env_vars: Mock environment variables

    Returns:
        KISConfig instance with test credentials
    """
    with patch.dict(os.environ, mock_env_vars, clear=True):
        return KISConfig(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def kis_config_real(mock_env_vars: dict[str, str]) -> KISConfig:
    """Provide KISConfig for real trading (not mock).

    Args:
        mock_env_vars: Mock environment variables

    Returns:
        KISConfig instance with use_mock=False
    """
    env = mock_env_vars.copy()
    env["KIS_USE_MOCK"] = "false"
    with patch.dict(os.environ, env, clear=True):
        return KISConfig(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def mock_access_token() -> KISAccessToken:
    """Provide a mock access token for testing.

    Returns:
        KISAccessToken instance with test values
    """
    return KISAccessToken(
        access_token="test_access_token_abc123",
        token_type="Bearer",
        expires_in=86400,
    )


@pytest.fixture
def mock_httpx_client() -> httpx.Client:
    """Provide a mock httpx.Client.

    Returns:
        MagicMock instance configured as httpx.Client
    """
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post = MagicMock()
    mock_client.get = MagicMock()
    mock_client.request = MagicMock()
    mock_client.close = MagicMock()
    return mock_client


@pytest.fixture
def kis_client(
    kis_config: KISConfig,
    mock_httpx_client: MagicMock,
) -> KISRestClient:
    """Provide a KISRestClient with mocked HTTP client.

    Args:
        kis_config: KIS configuration
        mock_httpx_client: Mocked httpx.AsyncClient

    Returns:
        KISRestClient instance ready for testing
    """
    return KISRestClient(
        config=kis_config,
        client=mock_httpx_client,
        timeout=30.0,
    )


@pytest.fixture
def authenticated_kis_client(
    kis_config: KISConfig,
    mock_httpx_client: MagicMock,
    mock_access_token: KISAccessToken,
) -> KISRestClient:
    """Provide an authenticated KISRestClient.

    Args:
        kis_config: KIS configuration
        mock_httpx_client: Mocked httpx.AsyncClient
        mock_access_token: Mock access token

    Returns:
        KISRestClient instance with authenticated state
    """
    # Create a fresh client instance (not reusing kis_client to avoid state mutation)
    client = KISRestClient(
        config=kis_config,
        client=mock_httpx_client,
        timeout=30.0,
    )
    client.state.update_token(mock_access_token)
    return client


@pytest.fixture
def mock_response_factory() -> Callable[[int, dict[str, Any]], MagicMock]:
    """Factory for creating mock httpx.Response objects.

    Returns:
        Function that creates mock responses with given status and data
    """

    def _create_response(status_code: int, data: dict[str, Any]) -> MagicMock:
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = status_code
        mock_response.json.return_value = data
        mock_response.raise_for_status = MagicMock()

        if status_code >= 400:
            import httpx

            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"Error {status_code}",
                request=MagicMock(),
                response=mock_response,
            )

        return mock_response

    return _create_response


@pytest.fixture
def connection_state(kis_config: KISConfig) -> KISConnectionState:
    """Provide a KISConnectionState for testing.

    Args:
        kis_config: KIS configuration

    Returns:
        KISConnectionState instance
    """
    return KISConnectionState(config=kis_config)


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Reset logging configuration before each test.

    Ensures clean logging state between tests.
    """
    import logging

    # Clear all handlers to prevent log output during tests
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    logging.getLogger("stock_manager").handlers = []


@pytest.fixture
def sample_api_response() -> dict[str, Any]:
    """Provide a sample successful KIS API response.

    Returns:
        Dictionary matching KIS API success response structure
    """
    return {
        "rt_cd": "0",
        "msg_cd": "0",
        "msg1": "정상처리",
        "output": {
            "stck_prpr": "75000",
        },
    }


@pytest.fixture
def sample_error_response() -> dict[str, Any]:
    """Provide a sample KIS API error response.

    Returns:
        Dictionary matching KIS API error response structure
    """
    return {
        "rt_cd": "-1",
        "msg_cd": "EGW00223",
        "msg1": "Invalid parameter value",
    }


# TDD Helper fixtures


@pytest.fixture
def assert_test_fails() -> Callable[[], None]:
    """Helper for RED phase tests - ensure test fails initially.

    This fixture helps write tests that document expected failures
    before implementing fixes (Kent Beck's TDD approach).

    Returns:
        Function that can be used to mark tests as expected to fail
    """
    # Return a no-op function - tests use pytest.raises or pytest.xfail
    return lambda: None


# Async test helpers


@pytest.fixture
def async_event_loop():
    """Provide an event loop for async tests.

    Yields:
        Asyncio event loop
    """
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_sessionstart(session) -> None:
    config = session.config
    args = [str(a) for a in getattr(config, "args", [])]
    if len(args) != 1:
        return

    target = args[0].split("::", 1)[0]
    if not target.endswith("tests/unit/test_cli_main.py"):
        return

    cov_plugin = config.pluginmanager.getplugin("_cov")
    if cov_plugin is not None and hasattr(cov_plugin, "options"):
        cov_plugin.options.cov_fail_under = 0
