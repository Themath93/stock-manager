"""
Example test file demonstrating how to use KIS API response fixtures.

This file shows various usage patterns for the fixtures in kis_responses.py.
"""

import pytest
from tests.fixtures.kis_responses import (
    mock_inquire_balance_success,
    mock_inquire_current_price_success,
    mock_inquire_daily_price_success,
    mock_cash_order_success,
    mock_balance_sheet_success,
    mock_income_statement_success,
    mock_financial_ratio_success,
    mock_error_response,
    mock_auth_error,
    mock_invalid_stock_code_error,
    mock_insufficient_balance_error,
    create_balance_position,
    create_custom_balance,
    get_test_stock_info,
    TEST_STOCKS,
)


class TestKISResponseFixtures:
    """Example tests demonstrating fixture usage."""

    def test_balance_inquiry_success(self):
        """Test using balance inquiry success fixture."""
        response = mock_inquire_balance_success()

        assert response["rt_cd"] == "0"
        assert response["msg_cd"] == "MCA00000"
        assert len(response["output1"]) == 2  # Two positions

        # Check Samsung Electronics position
        samsung = response["output1"][0]
        assert samsung["pdno"] == "005930"
        assert samsung["prdt_name"] == "삼성전자"
        assert int(samsung["hldg_qty"]) == 10

    def test_current_price_success(self):
        """Test using current price success fixture."""
        response = mock_inquire_current_price_success(
            stock_code="005930",
            current_price=75000,
            prev_close=73000
        )

        assert response["rt_cd"] == "0"
        assert response["output"]["stck_shrn_iscd"] == "005930"
        assert response["output"]["stck_prpr"] == "75000"
        assert response["output"]["prdy_vrss_sign"] == "2"  # Price up

    def test_daily_price_history(self):
        """Test using daily price history fixture."""
        response = mock_inquire_daily_price_success(
            stock_code="005930",
            days=5
        )

        assert response["rt_cd"] == "0"
        assert len(response["output"]) == 5

        # Check first day data
        first_day = response["output"][0]
        assert "stck_bsop_date" in first_day
        assert "stck_clpr" in first_day
        assert "acml_vol" in first_day

    def test_order_success(self):
        """Test using order success fixture."""
        response = mock_cash_order_success(
            order_no="0000012345",
            stock_code="005930",
            order_qty=10,
            order_price=75000
        )

        assert response["rt_cd"] == "0"
        assert response["output"]["ODNO"] == "0000012345"
        assert response["msg1"] == "정상처리 되었습니다."

    def test_balance_sheet_data(self):
        """Test using balance sheet fixture."""
        response = mock_balance_sheet_success(stock_code="005930")

        assert response["rt_cd"] == "0"
        assert len(response["output"]) > 0

        # Check for key financial statement items
        items = {item["acct_nm"] for item in response["output"]}
        assert "현금및현금성자산" in items
        assert "자산총계" in items
        assert "자본총계" in items

    def test_income_statement_data(self):
        """Test using income statement fixture."""
        response = mock_income_statement_success(stock_code="005930")

        assert response["rt_cd"] == "0"
        assert len(response["output"]) > 0

        # Check for key income statement items
        items = {item["acct_nm"] for item in response["output"]}
        assert "매출액" in items
        assert "영업이익" in items
        assert "당기순이익" in items

    def test_financial_ratios(self):
        """Test using financial ratio fixture."""
        response = mock_financial_ratio_success(stock_code="005930")

        assert response["rt_cd"] == "0"
        assert len(response["output"]) > 0

        # Check for key financial ratios
        ratios = {item["acct_nm"] for item in response["output"]}
        assert "ROE" in ratios
        assert "ROA" in ratios
        assert "부채비율" in ratios

    def test_error_responses(self):
        """Test various error response fixtures."""
        # Generic error
        error = mock_error_response()
        assert error["rt_cd"] == "-1"
        assert error["msg_cd"] == "EGW00123"

        # Auth error
        auth_error = mock_auth_error()
        assert auth_error["rt_cd"] == "-1"
        assert "인증" in auth_error["msg1"]

        # Invalid stock code
        invalid_code = mock_invalid_stock_code_error()
        assert invalid_code["rt_cd"] == "1"
        assert "종목코드" in invalid_code["msg1"]

        # Insufficient balance
        insufficient = mock_insufficient_balance_error()
        assert insufficient["rt_cd"] == "1"
        assert "초과" in insufficient["msg1"]

    def test_custom_balance_creation(self):
        """Test creating custom balance with factory functions."""
        # Create custom positions
        position1 = create_balance_position(
            stock_code="005930",
            stock_name="삼성전자",
            quantity=10,
            avg_price=70000,
            current_price=75000
        )

        position2 = create_balance_position(
            stock_code="035420",
            stock_name="NAVER",
            quantity=5,
            avg_price=200000,
            current_price=210000
        )

        # Create custom balance response
        balance = create_custom_balance(
            positions=[position1, position2],
            cash_balance=5000000
        )

        assert balance["rt_cd"] == "0"
        assert len(balance["output1"]) == 2
        assert balance["output1"][0]["pdno"] == "005930"
        assert balance["output1"][1]["pdno"] == "035420"

    def test_stock_info_lookup(self):
        """Test stock information lookup."""
        # Get Samsung Electronics info
        samsung = get_test_stock_info("005930")
        assert samsung is not None
        assert samsung["name"] == "삼성전자"
        assert samsung["price"] == 75000

        # Get NAVER info
        naver = get_test_stock_info("035420")
        assert naver is not None
        assert naver["name"] == "NAVER"

        # Non-existent stock
        unknown = get_test_stock_info("999999")
        assert unknown is None

    def test_test_stocks_constant(self):
        """Test TEST_STOCKS constant."""
        assert len(TEST_STOCKS) == 10
        assert "005930" in TEST_STOCKS
        assert "000660" in TEST_STOCKS
        assert TEST_STOCKS["005930"]["name"] == "삼성전자"


class TestMockingPatterns:
    """Example patterns for mocking API calls in tests."""

    def test_mock_with_pytest_monkeypatch(self, monkeypatch):
        """Example: Mock API call using pytest monkeypatch."""
        def mock_api_call(*args, **kwargs):
            return mock_inquire_current_price_success()

        # monkeypatch.setattr("module.function", mock_api_call)
        # Your test code here
        response = mock_api_call()
        assert response["rt_cd"] == "0"

    def test_mock_with_unittest_mock(self):
        """Example: Mock API call using unittest.mock."""
        from unittest.mock import Mock

        mock_client = Mock()
        mock_client.make_request.return_value = mock_inquire_balance_success()

        # Use the mock in your test
        response = mock_client.make_request(method="GET", path="/balance")
        assert response["rt_cd"] == "0"
        assert len(response["output1"]) == 2

    def test_parameterized_fixtures(self):
        """Example: Using parameterized fixtures."""
        test_cases = [
            ("005930", 75000),
            ("000660", 135000),
            ("035420", 210000),
        ]

        for stock_code, expected_price in test_cases:
            stock_info = get_test_stock_info(stock_code)
            assert stock_info is not None
            assert stock_info["price"] == expected_price


class TestErrorHandling:
    """Example patterns for testing error handling."""

    def test_handle_auth_error(self):
        """Example: Test handling authentication errors."""
        error_response = mock_auth_error()

        # Your error handling logic
        if error_response["rt_cd"] != "0":
            # Handle error
            assert "인증" in error_response["msg1"]
            # Raise exception or return error state
            pass

    def test_handle_rate_limit(self):
        """Example: Test handling rate limit errors."""
        from tests.fixtures.kis_responses import mock_rate_limit_error

        error_response = mock_rate_limit_error()

        if error_response["rt_cd"] != "0":
            assert "한도" in error_response["msg1"]
            # Implement retry logic or backoff strategy
            pass

    def test_handle_market_closed(self):
        """Example: Test handling market closed errors."""
        from tests.fixtures.kis_responses import mock_market_closed_error

        error_response = mock_market_closed_error()

        if error_response["rt_cd"] != "0":
            assert "장운영시간" in error_response["msg1"]
            # Handle market closed scenario
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
