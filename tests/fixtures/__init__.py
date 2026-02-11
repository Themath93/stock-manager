"""
Test fixtures for KIS API responses.

This package provides reusable mock API responses for testing.
"""

from tests.fixtures.kis_responses import (
    # Success fixtures
    mock_inquire_balance_success,
    mock_inquire_current_price_success,
    mock_inquire_daily_price_success,
    mock_cash_order_success,
    mock_balance_sheet_success,
    mock_income_statement_success,
    mock_financial_ratio_success,
    # Error fixtures
    mock_error_response,
    mock_auth_error,
    mock_invalid_stock_code_error,
    mock_insufficient_balance_error,
    mock_market_closed_error,
    mock_rate_limit_error,
    # Factory functions
    create_balance_position,
    create_custom_balance,
    get_test_stock_info,
    # Constants
    TEST_STOCKS,
)

__all__ = [
    # Success fixtures
    "mock_inquire_balance_success",
    "mock_inquire_current_price_success",
    "mock_inquire_daily_price_success",
    "mock_cash_order_success",
    "mock_balance_sheet_success",
    "mock_income_statement_success",
    "mock_financial_ratio_success",
    # Error fixtures
    "mock_error_response",
    "mock_auth_error",
    "mock_invalid_stock_code_error",
    "mock_insufficient_balance_error",
    "mock_market_closed_error",
    "mock_rate_limit_error",
    # Factory functions
    "create_balance_position",
    "create_custom_balance",
    "get_test_stock_info",
    # Constants
    "TEST_STOCKS",
]
