"""Tests for KISRestClient.

Following Kent Beck's TDD methodology:
- RED: Write failing tests first
- GREEN: Make tests pass
- REFACTOR: Improve while keeping tests green
"""

from unittest.mock import MagicMock

import pytest
import httpx

from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
from stock_manager.adapters.broker.kis.exceptions import (
    KISAPIError,
    KISAuthenticationError,
    KISRateLimitError,
)


class TestKISRestClientInit:
    """Tests for KISRestClient initialization."""

    def test_client_init_with_config(
        self,
        kis_config: KISConfig,
    ) -> None:
        """Test client initialization with valid config."""
        client = KISRestClient(config=kis_config)

        assert client.config is kis_config
        assert client.state.config is kis_config
        assert client.timeout == 30.0
        assert client.state.access_token is None
        assert client.state.is_authenticated is False

    def test_client_init_with_custom_timeout(
        self,
        kis_config: KISConfig,
    ) -> None:
        """Test client initialization with custom timeout."""
        client = KISRestClient(config=kis_config, timeout=60.0)

        assert client.timeout == 60.0

    def test_client_init_with_custom_http_client(
        self,
        kis_config: KISConfig,
    ) -> None:
        """Test client initialization with custom HTTP client."""
        mock_client = MagicMock(spec=httpx.Client)

        client = KISRestClient(config=kis_config, client=mock_client)

        assert client._http_client is mock_client

    def test_client_default_headers(self, kis_config: KISConfig) -> None:
        """Test default headers are set correctly."""
        client = KISRestClient(config=kis_config)

        headers = client._get_default_headers()

        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers


class TestKISRestClientAuthenticate:
    """Tests for client authentication."""

    def test_authenticate_success(
        self,
        kis_client: KISRestClient,
        mock_access_token: KISAccessToken,
    ) -> None:
        """Test successful authentication."""
        # Arrange
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.oauth_token_response(
            access_token=mock_access_token.access_token,
            expires_in=mock_access_token.expires_in,
        )

        kis_client._http_client.post.return_value = mock_response

        # Act
        token = kis_client.authenticate()

        # Assert
        assert token.access_token == mock_access_token.access_token
        assert token.token_type == "Bearer"
        assert kis_client.state.is_authenticated is True
        assert kis_client.state.access_token is not None

    def test_authenticate_sets_state(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test authentication updates connection state."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.oauth_token_response()

        kis_client._http_client.post.return_value = mock_response

        kis_client.authenticate()

        assert kis_client.state.is_authenticated is True
        assert kis_client.state.access_token is not None

    def test_authenticate_http_error(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test authentication with HTTP error."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.unauthorized()
        kis_client._http_client.post.return_value = mock_response

        with pytest.raises(KISAuthenticationError):
            kis_client.authenticate()

    def test_authenticate_invalid_response(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test authentication with invalid token response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.raise_for_status = MagicMock()
        kis_client._http_client.post.return_value = mock_response

        with pytest.raises(KISAuthenticationError, match="missing access_token"):
            kis_client.authenticate()

    def test_authenticate_network_error(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test authentication with network error."""
        kis_client._http_client.post.side_effect = httpx.RequestError("Network error")

        with pytest.raises(KISAPIError, match="Network error"):
            kis_client.authenticate()


class TestKISRestClientMakeRequest:
    """Tests for API request handling."""

    def test_make_request_success(
        self,
        authenticated_kis_client: KISRestClient,
        sample_api_response: dict,
    ) -> None:
        """Test successful API request."""
        # Arrange
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.success_kis(
            output=sample_api_response.get("output", {})
        )
        authenticated_kis_client._http_client.request.return_value = mock_response

        # Act
        result = authenticated_kis_client.make_request(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            params={"FID_COND_MRKT_DIV_CODE": "J"},
        )

        # Assert
        assert result["rt_cd"] == "0"
        assert authenticated_kis_client._http_client.request.called

    def test_make_request_without_auth(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test request without authentication fails."""
        # Don't authenticate the client

        with pytest.raises(KISAuthenticationError, match="not authenticated"):
            kis_client.make_request(
                "GET",
                "/uapi/domestic-stock/v1/quotations/inquire-price",
            )

    def test_make_request_rate_limit(
        self,
        authenticated_kis_client: KISRestClient,
    ) -> None:
        """Test rate limit handling."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.rate_limit()
        authenticated_kis_client._http_client.request.return_value = mock_response

        with pytest.raises(KISRateLimitError, match="rate limit"):
            authenticated_kis_client.make_request(
                "GET",
                "/uapi/domestic-stock/v1/quotations/inquire-price",
            )

    def test_make_request_kis_error_response(
        self,
        authenticated_kis_client: KISRestClient,
    ) -> None:
        """Test KIS API error in response body (HTTP 200 with error)."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.kis_error()
        authenticated_kis_client._http_client.request.return_value = mock_response

        with pytest.raises(KISAPIError, match="Invalid parameter"):
            authenticated_kis_client.make_request(
                "GET",
                "/uapi/domestic-stock/v1/quotations/inquire-price",
            )

    def test_make_request_with_custom_headers(
        self,
        authenticated_kis_client: KISRestClient,
        sample_api_response: dict,
    ) -> None:
        """Test request with custom headers."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.success_kis()
        authenticated_kis_client._http_client.request.return_value = mock_response

        authenticated_kis_client.make_request(
            "GET",
            "/test",
            headers={"tr_id": "TTTC0001"},
        )

        # Verify custom headers were included
        call_args = authenticated_kis_client._http_client.request.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "tr_id" in headers

    def test_make_request_without_auth_required(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test request with require_auth=False."""
        from tests.factories.mock_responses import MockResponseFactory

        mock_response = MockResponseFactory.success_kis()
        kis_client._http_client.request.return_value = mock_response

        # Should not raise authentication error
        result = kis_client.make_request(
            "GET",
            "/test",
            require_auth=False,
        )

        assert result is not None


class TestKISRestClientHelpers:
    """Tests for client helper methods."""

    def test_get_auth_headers_when_authenticated(
        self,
        authenticated_kis_client: KISRestClient,
    ) -> None:
        """Test getting auth headers when authenticated."""
        headers = authenticated_kis_client._get_auth_headers()

        assert "Authorization" in headers
        assert "appkey" in headers
        assert "appsecret" in headers
        assert headers["Authorization"].startswith("Bearer ")

    def test_get_auth_headers_when_not_authenticated(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test getting auth headers when not authenticated raises error."""
        with pytest.raises(KISAuthenticationError, match="not authenticated"):
            kis_client._get_auth_headers()

    def test_is_error_response_detects_kis_errors(
        self,
        kis_client: KISRestClient,
        sample_error_response: dict,
    ) -> None:
        """Test error detection in KIS API responses."""
        assert kis_client._is_error_response(sample_error_response) is True

    def test_is_error_response_passes_success(
        self,
        kis_client: KISRestClient,
        sample_api_response: dict,
    ) -> None:
        """Test success response is not detected as error."""
        assert kis_client._is_error_response(sample_api_response) is False

    def test_create_api_error_from_response(
        self,
        kis_client: KISRestClient,
        sample_error_response: dict,
    ) -> None:
        """Test creating API error from response data."""
        error = kis_client._create_api_error_from_response(sample_error_response)

        assert isinstance(error, KISAPIError)
        assert error.error_code == "EGW00223"

    def test_is_authenticated(
        self,
        kis_client: KISRestClient,
        authenticated_kis_client: KISRestClient,
    ) -> None:
        """Test is_authenticated property."""
        assert kis_client.is_authenticated() is False
        assert authenticated_kis_client.is_authenticated() is True

    def test_get_access_token(
        self,
        kis_client: KISRestClient,
        mock_access_token: KISAccessToken,
    ) -> None:
        """Test get_access_token returns current token."""
        kis_client.state.update_token(mock_access_token)

        token = kis_client.get_access_token()

        assert token is mock_access_token


class TestKISRestClientContextManager:
    """Tests for context manager support."""

    def test_context_manager(
        self,
        kis_config: KISConfig,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Test using client as context manager."""
        with KISRestClient(config=kis_config, client=mock_httpx_client) as client:
            assert client is not None
            assert isinstance(client, KISRestClient)

        # Verify close was called
        assert mock_httpx_client.close.called

    def test_close_method(
        self,
        kis_client: KISRestClient,
    ) -> None:
        """Test close method."""
        kis_client.close()

        assert kis_client._http_client.close.called
