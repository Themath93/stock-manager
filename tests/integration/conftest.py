"""
Shared fixtures for integration tests

Provides common fixtures used across integration tests including
mock configurations, database connections, and test utilities.
"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

from dotenv import load_dotenv
import pytest

# Load environment variables from .env file
load_dotenv()

from stock_manager.adapters.broker.kis.kis_config import KISConfig
from stock_manager.adapters.broker.kis.kis_broker_adapter import KISBrokerAdapter
from stock_manager.adapters.broker.kis.kis_rest_client import KISRestClient
from stock_manager.adapters.broker.kis.kis_websocket_client import KISWebSocketClient
from stock_manager.adapters.broker.port.broker_port import (
    AuthenticationToken,
    OrderRequest,
    OrderSide,
    OrderType,
)


# ===== Test Configuration =====

@pytest.fixture
def test_config() -> KISConfig:
    """Create test KISConfig with all required fields"""
    # Use environment variables if available, otherwise use test values
    return KISConfig(
        kis_mode="PAPER",
        kis_app_key="test_app_key",
        kis_app_secret="test_app_secret",
        slack_bot_token="test_slack_token",
        slack_channel_id="test_channel_id",
    )


@pytest.fixture
def test_account_id() -> str:
    """Test account ID (10 digit numeric)"""
    return "1234567890"


# ===== Mock Client Fixtures =====

@pytest.fixture
def mock_rest_client(test_config: KISConfig) -> Mock:
    """Mock KISRestClient with all necessary methods"""
    mock_client = Mock(spec=KISRestClient)
    mock_client.config = test_config

    # Set up token to avoid refresh during tests
    mock_client.token_manager = Mock()
    mock_client.token_manager._token = AuthenticationToken(
        access_token="test_access_token",
        token_type="Bearer",
        expires_in=3600,
        expires_at=datetime.now() + timedelta(hours=1),
    )

    # Mock common methods
    mock_client.get_access_token.return_value = mock_client.token_manager._token
    mock_client.get_approval_key.return_value = "test_approval_key_12345"
    mock_client.get_hashkey.return_value = "test_hash_key"

    # Mock order methods
    mock_client.place_order.return_value = "ORDER12345"
    mock_client.cancel_order.return_value = True
    mock_client.get_orders.return_value = []
    mock_client.get_cash.return_value = Decimal("100000000")
    mock_client.get_stock_balance.return_value = []

    return mock_client


@pytest.fixture
def mock_ws_client() -> Mock:
    """Mock KISWebSocketClient with all necessary methods"""
    mock_client = Mock(spec=KISWebSocketClient)
    mock_client.connect_websocket.return_value = None
    mock_client.disconnect_websocket.return_value = None
    mock_client.subscribe_quotes.return_value = None
    mock_client.subscribe_executions.return_value = None
    return mock_client


# ===== KISBrokerAdapter Fixtures =====

@pytest.fixture
def broker_adapter(
    test_config: KISConfig,
    test_account_id: str,
    mock_rest_client: Mock,
) -> KISBrokerAdapter:
    """Create KISBrokerAdapter with mocked dependencies"""
    adapter = KISBrokerAdapter(config=test_config, account_id=test_account_id)
    adapter.rest_client = mock_rest_client
    adapter.ws_client = None
    adapter._initialized = False
    return adapter


# ===== Mock API Response Fixtures =====

@pytest.fixture
def mock_token_response() -> dict:
    """Mock successful token response from KIS API"""
    return {
        "access_token": "test_access_token_12345",
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@pytest.fixture
def mock_approval_key_response() -> dict:
    """Mock successful approval_key response from KIS API"""
    return {
        "approval_key": "test_approval_key_abc123xyz789",
    }


@pytest.fixture
def mock_order_response() -> dict:
    """Mock successful order response from KIS API"""
    return {
        "rt_cd": "0",
        "msg1": "정상처리 되었습니다.",
        "output": {
            "ODNO": "ORDER12345",
            "ORD_TPS": "체결",
        },
    }


@pytest.fixture
def mock_cancel_success_response() -> dict:
    """Mock successful cancel response from KIS API"""
    return {
        "rt_cd": "0",
        "msg1": "정상처리 되었습니다.",
        "output": {
            "ODNO": "ORDER12345",
        },
    }


@pytest.fixture
def mock_orders_response() -> dict:
    """Mock orders list response from KIS API"""
    return {
        "rt_cd": "0",
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
        ],
    }


@pytest.fixture
def mock_cash_response() -> dict:
    """Mock cash balance response from KIS API"""
    return {
        "rt_cd": "0",
        "output": [
            {
                "dnca_tot_amt": "100000000",  # 총 예수금
                "pchs_amt_smtl_amt": "50000000",  # 주문 가능 금액
            }
        ],
    }


@pytest.fixture
def mock_balance_response() -> dict:
    """Mock stock balance response from KIS API"""
    return {
        "rt_cd": "0",
        "output1": [
            {
                "pdno": "005930",  # 종목코드
                "prdt_name": "삼성전자",  # 종목명
                "hldg_qty": "10",  # 보유 수량
                "pchs_avg_pric": "80000",  # 매입 평균 가격
                "pchs_amt": "800000",  # 매입 금액
                "prpr": "85000",  # 현재가
                "evlu_amt": "850000",  # 평가 금액
                "evlu_pfls_amt": "50000",  # 평가 손익금액
                "evlu_pfls_rt": "6.25",  # 평가 손익율
            }
        ],
    }


# ===== Order Request Fixtures =====

@pytest.fixture
def sample_order_request() -> OrderRequest:
    """Sample order request for testing"""
    return OrderRequest(
        account_id="1234567890",
        symbol="005930",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        qty=Decimal("10"),
        price=Decimal("80000"),
        idempotency_key="test_order_001",
    )


@pytest.fixture
def sample_market_order_request() -> OrderRequest:
    """Sample market order request for testing"""
    return OrderRequest(
        account_id="1234567890",
        symbol="005930",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("10"),
        price=None,
        idempotency_key="test_market_order_001",
    )


# ===== Logging Fixtures =====

@pytest.fixture
def caplog_setup(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Setup log capture for testing"""
    caplog.set_level(logging.INFO)
    return caplog


# ===== Database Fixtures =====

@pytest.fixture(scope="module")
def test_db_url() -> str:
    """Get test database URL from environment or use default"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/stock_manager_test"
    )


# ===== Integration Test Marker =====

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
