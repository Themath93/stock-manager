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

    # TAG-001: SPEC-BACKEND-API-001 Task-001 approval_key 발급 단위 테스트
    @patch("httpx.Client.request")
    def test_get_approval_key_success(self, mock_request, client):
        """approval_key 발급 성공 테스트"""
        # Mock approval key response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"approval_key": "test_approval_key_12345"}
        mock_request.return_value = mock_response

        approval_key = client.get_approval_key()

        assert approval_key == "test_approval_key_12345"
        assert mock_request.called

    @patch("httpx.Client.request")
    def test_get_approval_key_missing_in_response(self, mock_request, client):
        """approval_key 발급 응답에 approval_key가 없을 때 AuthenticationError 발생"""
        # Mock response without approval_key
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {}
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client.get_approval_key()

        assert "approval_key not found in response" in str(exc_info.value)

    @patch("httpx.Client.request")
    def test_get_approval_key_api_failure(self, mock_request, client):
        """approval_key 발급 API 실패 시 AuthenticationError 발생"""
        # Mock API failure
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            client.get_approval_key()

        assert "Approval key generation failed" in str(exc_info.value)

    # TAG-001: SPEC-BACKEND-API-001 Task-002 해시키 생성 단위 테스트
    @patch("httpx.Client.request")
    def test_get_hashkey_success(self, mock_request, client):
        """해시키 발급 성공 테스트"""
        # Mock hashkey response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"HASH": "test_hash_key_abc123"}
        mock_request.return_value = mock_response

        request_body = {"test": "data"}
        hashkey = client.get_hashkey(request_body)

        assert hashkey == "test_hash_key_abc123"

    @patch("httpx.Client.request")
    def test_get_hashkey_failure_returns_empty_string(self, mock_request, client):
        """해시키 발급 실패 시 빈 문자열 반환 (경우 처리)"""
        # Mock API failure
        mock_request.side_effect = Exception("Network error")

        request_body = {"test": "data"}
        hashkey = client.get_hashkey(request_body)

        # 실패 시 빈 문자열 반환
        assert hashkey == ""

    @patch("httpx.Client.request")
    def test_get_hashkey_with_empty_body(self, mock_request, client):
        """빈 본문으로 해시키 발급 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"HASH": "empty_body_hash"}
        mock_request.return_value = mock_response

        hashkey = client.get_hashkey({})

        assert hashkey == "empty_body_hash"

    # TAG-001: SPEC-BACKEND-API-001 Task-004 토큰 갱신 단위 테스트
    def test_get_access_token_returns_cached_token(self, client):
        """get_access_token가 캐시된 토큰을 반환"""
        # Given: Token is already set
        client.token_manager._token = AuthenticationToken(
            access_token="cached_access_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )

        # When: get_access_token is called
        token = client.get_access_token()

        # Then: Return cached token
        assert token.access_token == "cached_access_token"

    def test_get_access_token_refreshes_when_needed(self, client):
        """get_access_token가 필요시 토큰 갱신"""
        # Given: Token is expiring soon
        client.token_manager._token = AuthenticationToken(
            access_token="old_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(minutes=4),
        )

        # Mock client.post for token refresh
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 86400,
        }

        mock_post = Mock(return_value=mock_response)
        client.client.post = mock_post

        # When: get_access_token is called
        token = client.get_access_token()

        # Then: Token should be refreshed
        assert token.access_token == "refreshed_token"


# TAG-001: SPEC-BACKEND-API-001 Task-005 통합 테스트
class TestKISRestClientIntegration:
    """KISRestClient 통합 테스트"""

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
        client_instance = KISRestClient(config)
        # Set token to avoid refresh
        client_instance.token_manager._token = AuthenticationToken(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            expires_at=datetime.now() + timedelta(hours=1),
        )
        return client_instance

    @patch("httpx.Client.request")
    def test_full_order_flow_with_hashkey(self, mock_request, client):
        """주문 전체 흐름 테스트 (해시키 포함)"""
        # Mock hashkey response
        mock_hashkey_response = Mock()
        mock_hashkey_response.status_code = 200
        mock_hashkey_response.json = lambda: {"HASH": "test_order_hash"}

        # Mock order response
        mock_order_response = Mock()
        mock_order_response.status_code = 200
        mock_order_response.json = lambda: {
            "output": {"ODNO": "ORDER12345"}
        }

        mock_request.side_effect = [mock_hashkey_response, mock_order_response]

        # Create order request
        order_request = OrderRequest(
            account_id="12345678123",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("10"),
            price=Decimal("80000"),
        )

        # Place order
        order_id = client.place_order(order_request)

        assert order_id == "ORDER12345"
        assert mock_request.call_count == 2

    @patch("httpx.Client.request")
    def test_cancel_order_flow(self, mock_request, client):
        """주문 취소 흐름 테스트"""
        # Mock cancel response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"rt_cd": "0"}
        mock_request.return_value = mock_response

        result = client.cancel_order("ORDER12345", "12345678123")

        assert result is True
        assert mock_request.called

    @patch("httpx.Client.request")
    def test_get_orders_flow(self, mock_request, client):
        """주문 목록 조회 흐름 테스트"""
        # Mock orders response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "output": [
                {
                    "ODNO": "ORDER12345",
                    "PDNO": "005930",
                    "SLL_BK_DVSN": "BUY",
                    "ORD_DVSN": "00",
                    "ORD_QTY": "10",
                    "ORD_UNPR": "80000",
                    "ORD_TPS": "체결",
                }
            ]
        }
        mock_request.return_value = mock_response

        orders = client.get_orders("12345678123")

        assert len(orders) == 1
        assert orders[0].broker_order_id == "ORDER12345"
        assert orders[0].symbol == "005930"

    @patch("httpx.Client.request")
    def test_get_cash_flow(self, mock_request, client):
        """예수금 조회 흐름 테스트"""
        # Mock cash response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "output": [
                {
                    "dnca_tot_amt": "100000000"
                }
            ]
        }
        mock_request.return_value = mock_response

        cash = client.get_cash("12345678123")

        assert cash == Decimal("100000000")

    @patch("httpx.Client.request")
    def test_get_stock_balance_flow(self, mock_request, client):
        """주식잔고 조회 흐름 테스트"""
        # Mock balance response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "output1": [
                {
                    "pdno": "005930",
                    "prdt_name": "삼성전자",
                    "hldg_qty": "100",
                    "pchs_avg_pric": "80000",
                    "pchs_amt": "8000000",
                    "prpr": "85000",
                    "evlu_amt": "8500000",
                    "evlu_pfls_amt": "500000",
                    "evlu_pfls_rt": "6.25",
                }
            ]
        }
        mock_request.return_value = mock_response

        balance = client.get_stock_balance("12345678123")

        assert len(balance) == 1
        assert balance[0]["pdno"] == "005930"
        assert balance[0]["hldg_qty"] == "100"
