# KIS API Response Fixtures

Reusable mock API responses for testing KIS (Korea Investment & Securities) OpenAPI integration.

## Overview

This package provides comprehensive fixtures for mocking KIS API responses in tests. All fixtures follow the standard KIS API response pattern:

```python
{
    "rt_cd": "0",       # Return code ("0" = success, non-zero = error)
    "msg_cd": "0",      # Message code
    "msg1": "OK",       # Message text
    "output": {...}     # Actual data payload
}
```

## Quick Start

```python
from tests.fixtures import (
    mock_inquire_balance_success,
    mock_inquire_current_price_success,
    mock_cash_order_success,
    create_custom_balance,
)

# Use pre-built fixtures
def test_balance_inquiry(mock_client):
    mock_client.make_request.return_value = mock_inquire_balance_success()

    response = mock_client.make_request(method="GET", path="/balance")
    assert response["rt_cd"] == "0"
    assert len(response["output1"]) == 2  # Two positions

# Create custom fixtures
def test_custom_balance():
    from tests.fixtures import create_balance_position

    position = create_balance_position(
        stock_code="005930",
        stock_name="삼성전자",
        quantity=10,
        avg_price=70000,
        current_price=75000
    )

    balance = create_custom_balance(
        positions=[position],
        cash_balance=5000000
    )
```

## Available Fixtures

### Success Response Fixtures

#### 1. Balance Inquiry

```python
from tests.fixtures import mock_inquire_balance_success

response = mock_inquire_balance_success()
# Returns account balance with 2 positions: Samsung Electronics and SK Hynix
```

**Response Structure:**
- `output1`: List of stock positions with P/L information
- `output2`: Account summary (cash, total assets, etc.)

#### 2. Current Price

```python
from tests.fixtures import mock_inquire_current_price_success

response = mock_inquire_current_price_success(
    stock_code="005930",
    stock_name="삼성전자",
    current_price=75000,
    opening_price=74500,
    high_price=76000,
    low_price=74000,
    prev_close=73000,
)
```

**Response Structure:**
- Current price, OHLC data
- Price change and rate from previous close
- Volume and trading amount
- Market indicators

#### 3. Daily Price History

```python
from tests.fixtures import mock_inquire_daily_price_success

response = mock_inquire_daily_price_success(
    stock_code="005930",
    days=5  # Number of days of historical data
)
```

**Response Structure:**
- Array of daily OHLC data
- Volume and trading amount per day

#### 4. Order Placement

```python
from tests.fixtures import mock_cash_order_success

response = mock_cash_order_success(
    order_no="0000012345",
    stock_code="005930",
    order_qty=10,
    order_price=75000,
    order_time="093015"
)
```

**Response Structure:**
- Order number
- Order timestamp

#### 5. Balance Sheet

```python
from tests.fixtures import mock_balance_sheet_success

response = mock_balance_sheet_success(stock_code="005930")
```

**Response Structure:**
- Current assets
- Non-current assets
- Total assets
- Liabilities
- Equity

#### 6. Income Statement

```python
from tests.fixtures import mock_income_statement_success

response = mock_income_statement_success(stock_code="005930")
```

**Response Structure:**
- Revenue (매출액)
- Cost of sales (매출원가)
- Gross profit (매출총이익)
- Operating income (영업이익)
- Net income (당기순이익)

#### 7. Financial Ratios

```python
from tests.fixtures import mock_financial_ratio_success

response = mock_financial_ratio_success(stock_code="005930")
```

**Response Structure:**
- Profitability ratios (ROE, ROA)
- Stability ratios (Debt ratio, Current ratio)
- Growth ratios
- Activity ratios

### Error Response Fixtures

```python
from tests.fixtures import (
    mock_error_response,
    mock_auth_error,
    mock_invalid_stock_code_error,
    mock_insufficient_balance_error,
    mock_market_closed_error,
    mock_rate_limit_error,
)

# Generic error
error = mock_error_response(
    rt_cd="-1",
    msg_cd="EGW00123",
    msg1="기타오류"
)

# Specific errors
auth_error = mock_auth_error()  # Authentication failed
invalid_code = mock_invalid_stock_code_error()  # Invalid stock code
insufficient = mock_insufficient_balance_error()  # Not enough balance
closed = mock_market_closed_error()  # Market is closed
rate_limit = mock_rate_limit_error()  # API rate limit exceeded
```

## Factory Functions

### Create Balance Position

Create individual stock positions for custom balance responses:

```python
from tests.fixtures import create_balance_position

position = create_balance_position(
    stock_code="005930",
    stock_name="삼성전자",
    quantity=10,
    avg_price=70000,
    current_price=75000
)
```

**Calculates automatically:**
- Purchase amount
- Evaluation amount
- Profit/loss
- Profit/loss rate

### Create Custom Balance

Combine multiple positions into a complete balance response:

```python
from tests.fixtures import create_balance_position, create_custom_balance

positions = [
    create_balance_position("005930", "삼성전자", 10, 70000, 75000),
    create_balance_position("035420", "NAVER", 5, 200000, 210000),
]

balance = create_custom_balance(
    positions=positions,
    cash_balance=5000000
)
```

**Calculates automatically:**
- Total purchase amount
- Total evaluation amount
- Total profit/loss
- Asset increase/decrease

## Test Stocks

Pre-defined test stocks with realistic prices:

```python
from tests.fixtures import TEST_STOCKS, get_test_stock_info

# Available stocks
TEST_STOCKS = {
    "005930": {"name": "삼성전자", "price": 75000},
    "000660": {"name": "SK하이닉스", "price": 135000},
    "035420": {"name": "NAVER", "price": 210000},
    "005380": {"name": "현대차", "price": 185000},
    "051910": {"name": "LG화학", "price": 420000},
    "006400": {"name": "삼성SDI", "price": 450000},
    "035720": {"name": "카카오", "price": 48000},
    "068270": {"name": "셀트리온", "price": 165000},
    "207940": {"name": "삼성바이오로직스", "price": 850000},
    "373220": {"name": "LG에너지솔루션", "price": 380000},
}

# Lookup stock info
stock_info = get_test_stock_info("005930")
# Returns: {"name": "삼성전자", "price": 75000}
```

## Usage Patterns

### Pattern 1: Mock with pytest monkeypatch

```python
def test_balance_inquiry(monkeypatch):
    from tests.fixtures import mock_inquire_balance_success

    def mock_api_call(*args, **kwargs):
        return mock_inquire_balance_success()

    monkeypatch.setattr("your_module.api_call", mock_api_call)

    # Your test code
    result = your_function()
    assert result is not None
```

### Pattern 2: Mock with unittest.mock

```python
from unittest.mock import Mock, patch
from tests.fixtures import mock_inquire_current_price_success

def test_current_price():
    with patch('your_module.KISRestClient') as mock_client:
        mock_client.return_value.make_request.return_value = \
            mock_inquire_current_price_success()

        # Your test code
        result = your_function()
        assert result["price"] == 75000
```

### Pattern 3: Parameterized tests

```python
import pytest
from tests.fixtures import get_test_stock_info, TEST_STOCKS

@pytest.mark.parametrize("stock_code", TEST_STOCKS.keys())
def test_all_stocks(stock_code):
    stock_info = get_test_stock_info(stock_code)
    assert stock_info is not None
    assert stock_info["price"] > 0
```

### Pattern 4: Custom scenarios

```python
from tests.fixtures import create_balance_position, create_custom_balance

def test_profit_scenario():
    """Test scenario with profitable positions."""
    positions = [
        create_balance_position("005930", "삼성전자", 10, 70000, 75000),  # +7.14%
        create_balance_position("000660", "SK하이닉스", 5, 130000, 135000),  # +3.85%
    ]
    balance = create_custom_balance(positions, cash_balance=10000000)

    # Verify total profit
    total_pl = int(balance["output2"][0]["evlu_pfls_smtl_amt"])
    assert total_pl > 0  # Profitable

def test_loss_scenario():
    """Test scenario with loss positions."""
    positions = [
        create_balance_position("005930", "삼성전자", 10, 80000, 75000),  # -6.25%
    ]
    balance = create_custom_balance(positions, cash_balance=10000000)

    # Verify loss
    total_pl = int(balance["output2"][0]["evlu_pfls_smtl_amt"])
    assert total_pl < 0  # Loss
```

## Real-World Examples

See `test_kis_responses_example.py` for comprehensive usage examples including:
- Basic fixture usage
- Custom balance creation
- Error handling patterns
- Mocking strategies
- Parameterized tests

## Contributing

When adding new fixtures:

1. Follow the KIS API response structure
2. Use realistic sample data
3. Include both success and error cases
4. Provide factory functions for customization
5. Document with examples

## Notes

- All prices are in Korean Won (KRW)
- Stock codes are 6-digit strings (e.g., "005930")
- Dates are in YYYYMMDD format (e.g., "20240115")
- Times are in HHMMSS format (e.g., "093015")
- Korean text is used for stock names and messages (matching real API)
