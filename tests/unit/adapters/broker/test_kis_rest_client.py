"""Unit tests for KISRestClient and TokenManager"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import httpx

from stock_manager.adapters.broker.kis import KISConfig, KISRestClient, Mode
from stock_manager.adapters.broker.kis.kis_rest_client import TokenManager
from stock_manager.adapters.broker.port import (
    APIError,
    AuthenticationError,
    AuthenticationToken,
    OrderRequest,
    OrderSide,
    OrderType,
)


class TestTokenManager:
    """TokenManager 테스트"""

    def test_get_token_returns_cached_token_when_valid(self):
        """토큰이 유효하면 캐시된 토큰 반환"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 1시간 후)
        from stock_manager.adapters.broker.port import AuthenticationToken

        token_manager._token = AuthenticationToken(
            access_token="cached_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        # 캐시된 토큰 확인
        token = token_manager.get_token()
        assert token.access_token == "cached_token"
        assert not client.post.called

    @patch("time.sleep")
    def test_get_token_refreshes_when_expiring_soon(self, mock_sleep):
        """토큰이 5분 내 만료이면 갱신"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        # Mock API response
        client.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_in": 86400,
            },
        )
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 4분 후)
        token_manager._token = AuthenticationToken(
            access_token="old_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )

        # 토큰 갱신 확인
        token = token_manager.get_token()
        assert token.access_token == "new_token"
        assert client.post.called

    def test_force_refresh_updates_token(self):
        """force_refresh가 토큰을 강제로 갱신"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        # Mock API response
        client.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "access_token": "force_refreshed_token",
                "token_type": "Bearer",
                "expires_in": 86400,
            },
        )
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 4분 후)
        token_manager._token = AuthenticationToken(
            access_token="old_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )

        # 강제 갱신
        token_manager.force_refresh()
        token = token_manager.get_token()

        assert token.access_token == "force_refreshed_token"
        assert client.post.called

    def test_token_refresh_failure_raises_error(self):
        """토큰 갱신 실패 시 AuthenticationError 발생"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        # Mock API failure response
        client.post.return_value = Mock(
            status_code=401,
            text="Unauthorized",
        )
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 4분 후)
        token_manager._token = AuthenticationToken(
            access_token="old_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )

        # AuthenticationError 발생 확인
        with pytest.raises(AuthenticationError):
            token_manager.get_token()

    def test_needs_refresh_returns_false_when_token_valid(self):
        """토큰이 유효하면 갱신 필요 없음"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 1시간 후)
        from stock_manager.adapters.broker.port import AuthenticationToken

        token_manager._token = AuthenticationToken(
            access_token="valid_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=10),
        )

        # 갱신 필요 없음 확인
        assert not token_manager._needs_refresh()

    def test_needs_refresh_returns_true_when_token_expiring_soon(self):
        """토큰이 5분 내 만료이면 갱신 필요"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 4분 후)
        token_manager._token = AuthenticationToken(
            access_token="expiring_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )
        client = Mock(spec=httpx.Client)
        token_manager = TokenManager(config, client)

        # 토큰 초기화 (만료 4분 후)
        token_manager._token = AuthenticationToken(
            access_token="old_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )

        # 갱신 필요 확인
        assert token_manager._needs_refresh()

    def test_needs_refresh_returns_true_when_no_token(self):
        """토큰이 없으면 갱신 필요"""
        config = KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )
        client = Mock(spec=httpx.Client)
        token_manager = TokenManager(config, client)

        token_manager._token = None

        # 갱신 필요 확인
        assert token_manager._needs_refresh()


class TestKISRestClient:
    """KISRestClient 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return KISConfig(
            kis_app_key="test_key",
            kis_app_secret="test_secret",
        )

    @pytest.fixture
    def client(self, config):
        """테스트용 HTTP 클라이언트"""
        # Don't mock httpx, let it initialize normally
        # but set up token to avoid token refresh during tests
        client_instance = KISRestClient(config)
        # Set token to avoid refresh
        client_instance.token_manager._token = AuthenticationToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )
        return client_instance

    def test_client_initialization(self, config):
        """클라이언트 초기화 확인"""
        with patch("httpx.Client"):
            client = KISRestClient(config)
            assert client.config == config
            assert client.client is not None
            assert client.token_manager is not None

    def test_get_headers_includes_token(self, client):
        """헤더에 토큰 포함 확인"""
        # Mock 토큰
        client.token_manager._token = AuthenticationToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        headers = client._get_headers(include_token=True)

        assert "authorization" in headers
        assert headers["authorization"] == "Bearer test_token"
        assert headers["appkey"] == "test_key"
        assert headers["appsecret"] == "test_secret"

    def test_get_headers_excludes_token(self, client):
        """토큰 제외 헤더 확인"""
        headers = client._get_headers(include_token=False)

        assert "authorization" not in headers
        assert headers["appkey"] == "test_key"
        assert headers["appsecret"] == "test_secret"

    @patch("httpx.Client.request")
    def test_make_request_success(self, mock_request, client):
        """성공적인 API 요청"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"result": "success"}
        mock_request.return_value = mock_response

        response = client._make_request("GET", "/test")

        assert response == {"result": "success"}
        assert mock_request.called

    @patch("httpx.Client.request")
    def test_make_request_401_refreshes_token(self, mock_request, client):
        """401 오류 시 토큰 갱신 후 재시도"""
        # Mock 토큰 갱신
        mock_post = Mock()
        mock_post.return_value = Mock(
            json=lambda: {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_in": 86400,
            },
        )

        # Mock client.post method
        client.client.post = mock_post

        with patch.object(client.token_manager, "force_refresh"):
            # 첫 호출: 401, 두 번째 호출: 200
            mock_response_401 = Mock()
            mock_response_401.status_code = 401
            mock_response_401.text = "Unauthorized"

            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.json = lambda: {"result": "success"}

            mock_request.side_effect = [mock_response_401, mock_response_200]

            response = client._make_request("GET", "/test")

            assert response == {"result": "success"}
            assert mock_request.call_count == 2
            assert client.token_manager.force_refresh.called

    @patch("time.sleep")
    @patch("httpx.Client.request")
    def test_make_request_rate_limit_retry(self, mock_request, mock_sleep, client):
        """Rate Limit 시 재시도"""
        # 429 응답 후 200 응답
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json = lambda: {"result": "success"}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        response = client._make_request("GET", "/test", max_retries=2)

        assert response == {"result": "success"}
        assert mock_request.call_count == 2
        assert mock_sleep.called
