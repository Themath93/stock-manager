"""Test data factory for KIS API tests.

This module provides factory functions for creating test data,
following Kent Beck's TDD principle of explicit, simple test data.
"""

from datetime import datetime, timedelta
from typing import Any


class APITestDataFactory:
    """Factory for creating test data for KIS API tests.

    Provides realistic test data that matches KIS API specifications.
    """

    # Stock symbols
    STOCK_SAMSUNG = "005930"
    STOCK_LG_ES = "051910"
    STOCK_KAKAO = "035720"
    STOCK_NVDA = "NVDA"  # US stock
    STOCK_AAPL = "AAPL"  # US stock

    # Market codes
    MARKET_J = "J"  # KOSPI
    MARKET_Q = "Q"  # KOSDAQ
    MARKET_NYSE = "NYSE"
    MARKET_NASDAQ = "NASDAQ"

    @staticmethod
    def stock_price_data(
        symbol: str = STOCK_SAMSUNG,
        price: int = 75000,
        change: int = 500,
    ) -> dict[str, Any]:
        """Create stock price quote data.

        Args:
            symbol: Stock symbol
            price: Current price
            change: Price change

        Returns:
            Dictionary with stock price data
        """
        return {
            "stck_prpr": str(price),  # Current price
            "prdy_vrss": str(change),  # Change from previous close
            "prdy_vrss_sign": "2" if change > 0 else "1",  # Sign (2=up, 1=down)
            "prdy_ctrt": "0.67",  # Change percentage
            "stck_oprc": str(price - change),  # Open price
            "stck_hgpr": str(price + 1000),  # High price
            "stck_lwpr": str(price - 1000),  # Low price
            "acml_vol": "1000000",  # Accumulated volume
            "acml_tr_pbmn": "75000000000",  # Accumulated trading value
            "stck_sspr": str(price - 300),  # Previous close
        }

    @staticmethod
    def order_request(
        symbol: str = STOCK_SAMSUNG,
        quantity: int = 10,
        price: int | None = None,
        order_type: str = "buy",  # buy or sell
    ) -> dict[str, Any]:
        """Create an order request.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Price per share (None for market order)
            order_type: Order type (buy/sell)

        Returns:
            Dictionary with order request data
        """
        return {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "market_type": "limit" if price else "market",
        }

    @staticmethod
    def order_response(
        order_id: str = "12345",
        symbol: str = STOCK_SAMSUNG,
        quantity: int = 10,
        status: str = "confirmed",
    ) -> dict[str, Any]:
        """Create an order response.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            quantity: Number of shares
            status: Order status

        Returns:
            Dictionary with order response data
        """
        return {
            "odno": order_id,  # Order number
            "srtn_dn": str(quantity),  # Ordered quantity
            "ord_dt": datetime.now().strftime("%Y%m%d"),
            "ord_tmd": datetime.now().strftime("%H%M%S"),
            "ord_prc": "75000",  # Order price
            "ord_prc_cd": "00",  # Order code
            "pdyn": "N",  # Whether it's a day order
            "sll_buy_dvsn_cd": "02" if status == "buy" else "01",  # Buy/sell code
        }

    @staticmethod
    def account_balance(
        total_assets: int = 100000000,
        cash: int = 50000000,
        stock_value: int = 50000000,
    ) -> dict[str, Any]:
        """Create account balance data.

        Args:
            total_assets: Total asset value
            cash: Available cash
            stock_value: Stock holding value

        Returns:
            Dictionary with account balance data
        """
        return {
            "tot_evlu_amt": str(total_assets),  # Total evaluation amount
            "nass_amt": str(cash),  # Net asset sum
            "pchs_amt_smtl_amt": str(stock_value),  # Purchase amount total
            "evlu_pfls_amt": "1000000",  # Evaluation profit/loss amount
            "evlu_pfls_rt": "1.5",  # Evaluation profit/loss rate
            "scts_evlu_amt": str(stock_value),  # Securities evaluation amount
            "loan_amt": "0",  # Loan amount
            "dtl_1th_etf_alam_rl": "0",  # ETF alarm rate
            "thco_buy_am": "0",  # Total buy amount
            "thco_sll_am": "0",  # Total sell amount
            "tot_asst_evlu_amt": str(total_assets),  # Total asset evaluation amount
        }

    @staticmethod
    def holdings(
        symbol: str = STOCK_SAMSUNG,
        quantity: int = 100,
        avg_price: int = 72000,
        current_price: int = 75000,
    ) -> dict[str, Any]:
        """Create stock holdings data.

        Args:
            symbol: Stock symbol
            quantity: Number of shares held
            avg_price: Average purchase price
            current_price: Current market price

        Returns:
            Dictionary with holdings data
        """
        profit_amount = (current_price - avg_price) * quantity
        profit_rate = ((current_price - avg_price) / avg_price) * 100

        return {
            "prdt_name": "삼성전자",  # Product name
            "pdno": symbol,  # Product number (symbol)
            "prdt_pdcd": "KR7005930003",  # Product code
            "hldg_qty": str(quantity),  # Holding quantity
            "pchs_avg_pric": str(avg_price),  # Purchase average price
            "pchs_amt": str(avg_price * quantity),  # Purchase amount
            "prpr": str(current_price),  # Current price
            "evlu_amt": str(current_price * quantity),  # Evaluation amount
            "evlu_pfls_amt": str(profit_amount),  # Evaluation profit/loss amount
            "evlu_pfls_rt": f"{profit_rate:.2f}",  # Evaluation profit/loss rate
            "evlu_pfls_sign": "2" if profit_amount > 0 else "1",  # Profit/loss sign
            "sbp_prc": "0",  # Stop loss price
            "dlng_yd": "N",  # Whether it's a long-term holding
            "loan_dt": "",  # Loan date
            "stln_yn": "N",  # Whether settled
            "loan_ipyn_yn": "N",  # Whether loan is possible
            "stln_dtst_dcd": "00",  # Settlement date status code
            "stck_prc_hv_fluct_yn": "N",  # Whether price fluctuation is high
            "bas_pdcd": "KR7" + symbol[:4] + "0003",  # Base product code
            "cag_dt_by_spl_dtn_sn": "1",  # Categorization date serial number
            "fx_yn": "N",  # Whether FX is applicable
            "srtn_pdno": symbol,  # Short product number
            "pdyn_bsec_nm": "",  # Buying section name
            "evlu_pfls_sum_amt": "1000000",  # Evaluation profit/loss sum amount
            "stln_trvs_pfls_amt": "0",  # Settlement traverse profit/loss amount
            "adqn_sltr_qty": "0",  # Additional sell quantity
            "real_real_yn": "N",  # Whether real
            "bpsl_sltr_qty": "0",  # Buy possible sell quantity
            "trqt_sltr_qty": "0",  # Trading quantity sell quantity
            "hldg_dtil_sn": "1",  # Holding detail serial number
            "pt_ic_alyn_nm": "",  # PT IC alignment name
            "trqt_ic_alyn_nm": "",  # Trading quantity IC alignment name
            "adqn_ic_alyn_nm": "",  # Additional quantity IC alignment name
            "bpsl_ic_alyn_nm": "",  # Buy possible IC alignment name
            "cstdt_acmt_vol": "0",  # Custom date accumulated volume
            "yird_nwish_dvn_ictn_cd": "00",  # Year-end wish division division code
            "sbpp_rght_exrt_rt": "0",  # Subscription right execution rate
        }

    @staticmethod
    def candle_data(
        symbol: str = STOCK_SAMSUNG,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Create candlestick chart data.

        Args:
            symbol: Stock symbol
            days: Number of days of data

        Returns:
            List of daily OHLCV data
        """
        candles = []
        base_date = datetime.now() - timedelta(days=days)
        base_price = 75000

        for i in range(days):
            date = base_date + timedelta(days=i)
            # Random walk simulation
            import random

            change = random.randint(-500, 500)
            open_price = base_price + random.randint(-200, 200)
            close_price = open_price + change
            high_price = max(open_price, close_price) + random.randint(0, 300)
            low_price = min(open_price, close_price) - random.randint(0, 300)
            volume = random.randint(100000, 1000000)

            candles.append({
                "stck_dt": date.strftime("%Y%m%d"),
                "stck_oprc": str(open_price),  # Open
                "stck_hgpr": str(high_price),  # High
                "stck_lwpr": str(low_price),  # Low
                "stck_clpr": str(close_price),  # Close
                "acml_vol": str(volume),  # Volume
                "prdy_vrss": str(change),  # Change from previous close
                "prdy_vrss_sign": "2" if change > 0 else "1",  # Sign
                "prdy_ctrt": f"{abs(change) / base_price * 100:.2f}",  # Change rate
            })

            base_price = close_price

        return candles

    @staticmethod
    def oauth_token(
        access_token: str = "test_token_abc123",
        expires_in: int = 86400,
    ) -> dict[str, Any]:
        """Create OAuth token response data.

        Args:
            access_token: Access token string
            expires_in: Token lifetime in seconds

        Returns:
            Dictionary with OAuth token data
        """
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "token_type_bearer": "Bearer",
        }

    @staticmethod
    def invalid_params_response() -> dict[str, Any]:
        """Create an invalid parameters error response.

        Returns:
            Dictionary with KIS error structure
        """
        return {
            "rt_cd": "-1",
            "msg_cd": "EGW00223",
            "msg1": "Invalid parameter value",
            "output": {},
        }

    @staticmethod
    def auth_failed_response() -> dict[str, Any]:
        """Create an authentication failed response.

        Returns:
            Dictionary with auth error structure
        """
        return {
            "rt_cd": "-1",
            "msg_cd": "EGW00001",
            "msg1": "Authentication failed",
        }

    @staticmethod
    def rate_limit_response() -> dict[str, Any]:
        """Create a rate limit error response.

        Returns:
            Dictionary with rate limit error structure
        """
        return {
            "rt_cd": "-1",
            "msg_cd": "EGW00108",
            "msg1": "Exceeds the daily request limit",
        }

    @staticmethod
    def us_stock_quote(
        symbol: str = "NVDA",
        price: float = 875.50,
        change: float = 12.30,
    ) -> dict[str, Any]:
        """Create US stock quote data.

        Args:
            symbol: Stock symbol
            price: Current price
            change: Price change

        Returns:
            Dictionary with US stock quote data
        """
        return {
            "symbol": symbol,
            "last": str(price),
            "change": str(change),
            "change_rate": f"{change / (price - change) * 100:.2f}",
            "volume": "50000000",
            "open": str(price - 5),
            "high": str(price + 10),
            "low": str(price - 10),
            "time": datetime.now().strftime("%Y%m%d%H%M%S"),
        }


# Convenience functions for common test data


def sample_stock_price() -> dict[str, Any]:
    """Get sample stock price data."""
    return APITestDataFactory.stock_price_data()


def sample_order() -> dict[str, Any]:
    """Get sample order request."""
    return APITestDataFactory.order_request()


def sample_holdings() -> dict[str, Any]:
    """Get sample holdings data."""
    return APITestDataFactory.holdings()


def sample_oauth_token() -> dict[str, Any]:
    """Get sample OAuth token."""
    return APITestDataFactory.oauth_token()
