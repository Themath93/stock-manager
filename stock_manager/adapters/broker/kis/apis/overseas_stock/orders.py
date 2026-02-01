"""
KIS (Korea Investment & Securities) Overseas Stock Order/Account API Functions.

This module provides functions for overseas stock trading operations including
placing orders, managing positions, and account inquiries.

API Reference: https://apiportal.koreainvestment.com/
"""

from typing import Any, Dict, Literal


def place_overseas_order(
    client: Any,
    account_number: str,
    symbol: str,
    market_code: str,
    order_type: Literal["buy", "sell"],
    quantity: int,
    price: float,
    order_condition: Literal["00", "01", "02"] = "00",
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Place an overseas stock order (buy or sell).

    This function submits a buy or sell order for an overseas stock.
    Different TR_IDs are used based on the country and order type.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE' for Tokyo).
        order_type: Order type - 'buy' or 'sell'.
        quantity: Order quantity (number of shares).
        price: Order price per share.
        order_condition: Order condition code.
            '00' for limit, '01' for market, '02' for stop limit.
            Defaults to '00' (limit).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description
            - output (dict): Order confirmation data including:
                - ODNO (str): Order number
                - KRX_FMTG_ODNO (str): KRX formatted order number

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = place_overseas_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     order_type="buy",
        ...     quantity=10,
        ...     price=150.00,
        ...     is_paper_trading=True
        ... )
        >>> print(f"Order number: {response['output']['ODNO']}")

    Notes:
        - API ID: v1_해외주식-001
        - US Real Buy TR_ID: TTTT1002U, US Real Sell TR_ID: TTTT1006U
        - US Paper Buy TR_ID: VTTT1002U, US Paper Sell TR_ID: VTTT1001U
        - For Asian countries (Japan, China, Hong Kong, Vietnam), refer to the API spec.
        - URL: /uapi/overseas-stock/v1/trading/order
    """
    # Select TR_ID based on market and trading mode
    if is_paper_trading:
        if market_code in ["NASD", "NYSE", "AMEX", "S&P"]:
            tr_id = "VTTT1002U" if order_type == "buy" else "VTTT1001U"
        else:
            # Asian countries - use appropriate TR_ID
            tr_id = "VTTS3013U"  # Default for Asian markets
    else:
        if market_code in ["NASD", "NYSE", "AMEX", "S&P"]:
            tr_id = "TTTT1002U" if order_type == "buy" else "TTTT1006U"
        else:
            # Asian countries - use appropriate TR_ID
            tr_id = "TTTS3013U"  # Default for Asian markets

    # Build order type code
    ord_type = "00" if order_type == "buy" else "01"  # 00: buy, 01: sell

    data = {
        "CANO": account_number[:8],  # Account number (8 digits)
        "ACNT_PRDT_CD": "01",  # Account product code
        "PDNO": symbol,  # Symbol
        "ORD_DVSN": ord_type,  # Order division (00: buy, 01: sell)
        "ORD_QTY": str(quantity),  # Order quantity
        "ORD_UNPR": str(price),  # Order unit price
        "ORD_SVR_DVSN_CD": order_condition,  # Order condition (00: limit, 01: market, 02: stop limit)
        "ORD_TMD": "0",  # Order time division (0: regular, 2: after-hours)
        "EXCD": market_code,  # Exchange code
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/order",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def place_overseas_reservation_order(
    client: Any,
    account_number: str,
    symbol: str,
    market_code: str,
    order_type: Literal["buy", "sell"],
    quantity: int,
    price: float,
    execution_date: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Place a reservation order for overseas stock.

    This function submits a reservation order that will be executed at a specified
    future date. Different TR_IDs are used based on the country and order type.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE' for Tokyo).
        order_type: Order type - 'buy' or 'sell'.
        quantity: Order quantity (number of shares).
        price: Order price per share.
        execution_date: Execution date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing reservation order confirmation.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = place_overseas_reservation_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     order_type="buy",
        ...     quantity=10,
        ...     price=150.00,
        ...     execution_date="20240130",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-002
        - US Real Buy TR_ID: TTTT3014U, US Real Sell TR_ID: TTTT3016U
        - US Paper Buy TR_ID: VTTT3014U, US Paper Sell TR_ID: VTTT3016U
        - Asian Real TR_ID: TTTS3013U, Asian Paper TR_ID: VTTS3013U
        - URL: /uapi/overseas-stock/v1/trading/order-resv
    """
    # Select TR_ID based on market and trading mode
    if is_paper_trading:
        if market_code in ["NASD", "NYSE", "AMEX", "S&P"]:
            tr_id = "VTTT3014U" if order_type == "buy" else "VTTT3016U"
        else:
            tr_id = "VTTS3013U"  # For China/Hong Kong/Japan/Vietnam
    else:
        if market_code in ["NASD", "NYSE", "AMEX", "S&P"]:
            tr_id = "TTTT3014U" if order_type == "buy" else "TTTT3016U"
        else:
            tr_id = "TTTS3013U"  # For China/Hong Kong/Japan/Vietnam

    ord_type = "00" if order_type == "buy" else "01"

    data = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "PDNO": symbol,
        "ORD_DVSN": ord_type,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "EXCD": market_code,
        "RVSE_ORD_DT": execution_date,  # Reservation order date (YYYYMMDD)
        "ORD_SVR_DVSN_CD": "00",  # Order condition (00: limit)
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/order-resv",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def cancel_overseas_order(
    client: Any,
    account_number: str,
    order_number: str,
    symbol: str,
    market_code: str,
    original_order_type: Literal["buy", "sell"],
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Cancel an overseas stock order.

    This function cancels a previously placed overseas stock order.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        order_number: Original order number to cancel.
        symbol: Overseas stock symbol.
        market_code: Market code (e.g., 'NASD', 'NYSE').
        original_order_type: Original order type - 'buy' or 'sell'.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing cancellation confirmation.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = cancel_overseas_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     order_number="0000001234",
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     original_order_type="buy",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-003
        - US Real TR_ID: TTTT1004U, US Paper TR_ID: VTTT1004U
        - For Asian countries, refer to the API specification.
        - URL: /uapi/overseas-stock/v1/trading/order-rvsecncl
    """
    tr_id = "VTTT1004U" if is_paper_trading else "TTTT1004U"

    # For Asian markets, use different TR_IDs
    if market_code not in ["NASD", "NYSE", "AMEX", "S&P"]:
        tr_id = "VTTS1004U" if is_paper_trading else "TTTS1004U"

    data = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "ODNO": order_number,
        "PDNO": symbol,
        "ORD_DVSN": "00" if original_order_type == "buy" else "01",
        "EXCD": market_code,
        "RVSE_CNCL_DVSN_CD": "02",  # 02: cancel
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/order-rvsecncl",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def cancel_overseas_reservation_order(
    client: Any,
    account_number: str,
    reservation_order_number: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Cancel a reservation order for overseas stock.

    This function cancels a previously placed reservation order.
    Note: Only available for US markets.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        reservation_order_number: Reservation order number to cancel.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing cancellation confirmation.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = cancel_overseas_reservation_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     reservation_order_number="0000001234",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-004
        - US Real TR_ID: TTTT3017U, US Paper TR_ID: VTTT3017U
        - Not available for Asian countries.
        - URL: /uapi/overseas-stock/v1/trading/order-resv-ccnl
    """
    tr_id = "VTTT3017U" if is_paper_trading else "TTTT3017U"

    data = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "RVSE_ODNO": reservation_order_number,
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/order-resv-ccnl",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def get_overseas_unsettled_orders(
    client: Any,
    account_number: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get unsettled (pending) overseas stock orders.

    This function retrieves all pending orders that have not yet been executed
    or cancelled.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing unsettled order data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_unsettled_orders(
        ...     client=client,
        ...     account_number="12345678",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-005
        - Real TR_ID: TTTS3018R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/inquire-nccs
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "TTTS3018R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "CTX_AREA_FK100": "",  # Continuation key for pagination
        "CTX_AREA_NK100": "",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-nccs",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_balance(
    client: Any,
    account_number: str,
    market_code: str,
    currency_code: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get overseas stock holdings/balance.

    This function retrieves the current holdings of overseas stocks in the account.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        currency_code: Currency code (e.g., 'USD', 'JPY', 'HKD').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing balance information including:
            - Balance details
            - Holdings data
            - Valuation information

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_balance(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     currency_code="USD",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-006
        - Real TR_ID: TTTS3012R
        - Paper TR_ID: VTTS3012R
        - URL: /uapi/overseas-stock/v1/trading/inquire-balance
    """
    tr_id = "VTTS3012R" if is_paper_trading else "TTTS3012R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,  # Exchange code
        "SETT_CURRENCY_CD": currency_code,  # Settlement currency (USD, JPY, HKD, etc.)
        "CTX_AREA_FK100": "",  # Continuation key
        "CTX_AREA_NK100": "",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-balance",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_order_conclusion(
    client: Any,
    account_number: str,
    market_code: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get overseas stock order and conclusion history.

    This function retrieves the history of executed orders for the specified date range.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing order history data.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_order_conclusion(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     start_date="20240101",
        ...     end_date="20240131",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-007
        - Real TR_ID: TTTS3035R
        - Paper TR_ID: VTTS3035R
        - URL: /uapi/overseas-stock/v1/trading/inquire-ccnl
    """
    tr_id = "VTTS3035R" if is_paper_trading else "TTTS3035R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,
        "STRT_DT": start_date,  # Start date (YYYYMMDD)
        "END_DT": end_date,  # End date (YYYYMMDD)
        "CTX_AREA_FK100": "",  # Continuation key
        "CTX_AREA_NK100": "",
        "SORT_SQN": "DS",  # Sort sequence (DS: descending, AS: ascending)
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-ccnl",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_present_balance(
    client: Any,
    account_number: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get current balance based on conclusion (execution) for overseas stocks.

    This function retrieves the current account balance with real-time updates
    based on executed trades.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing current balance information.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_present_balance(
        ...     client=client,
        ...     account_number="12345678",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-008
        - Real TR_ID: CTRP6504R
        - Paper TR_ID: VTRP6504R
        - URL: /uapi/overseas-stock/v1/trading/inquire-present-balance
    """
    tr_id = "VTRP6504R" if is_paper_trading else "CTRP6504R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-present-balance",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_reservation_orders(
    client: Any,
    account_number: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stock reservation order list.

    This function retrieves all pending reservation orders for the account.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'TKSE', 'SHAI', 'HKEX', 'VNSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing reservation order list.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_reservation_orders(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-013
        - US Real TR_ID: TTTT3039R
        - Japan/China/Hong Kong/Vietnam Real TR_ID: TTTS3014R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/order-resv-list
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    # Select TR_ID based on market
    if market_code in ["NASD", "NYSE", "AMEX", "S&P"]:
        tr_id = "TTTT3039R"
    else:
        tr_id = "TTTS3014R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/order-resv-list",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_buyable_amount(
    client: Any,
    account_number: str,
    market_code: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get the maximum buyable amount for overseas stocks.

    This function retrieves information about the maximum amount available
    for purchasing overseas stocks.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing buyable amount information.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_buyable_amount(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: v1_해외주식-014
        - Real TR_ID: TTTS3007R
        - Paper TR_ID: VTTS3007R
        - URL: /uapi/overseas-stock/v1/trading/inquire-psamount
    """
    tr_id = "VTTS3007R" if is_paper_trading else "TTTS3007R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,
        "PDNO": "",  # Symbol (optional, leave empty for general inquiry)
        "ORD_UNPR": "0",  # Order unit price (0 for maximum quantity inquiry)
        "ORD_QTY": "0",  # Order quantity (0 for amount inquiry)
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-psamount",
        params=params,
        headers={"tr_id": tr_id},
    )


def place_overseas_daytime_order(
    client: Any,
    account_number: str,
    symbol: str,
    market_code: str,
    order_type: Literal["buy", "sell"],
    quantity: int,
    price: float,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Place a daytime (intraday) order for US stocks.

    This function allows placing orders during US daytime hours.
    Only available for US market stocks.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        symbol: US stock symbol (e.g., 'AAPL').
        market_code: Market code (must be US market like 'NASD', 'NYSE').
        order_type: Order type - 'buy' or 'sell'.
        quantity: Order quantity (number of shares).
        price: Order price per share.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing order confirmation.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = place_overseas_daytime_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     order_type="buy",
        ...     quantity=10,
        ...     price=150.00,
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-026
        - Real Buy TR_ID: TTTS6036U, Real Sell TR_ID: TTTS6037U
        - Paper TR_ID: Not Supported
        - Only available for US markets
        - URL: /uapi/overseas-stock/v1/trading/daytime-order
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    # Only US markets are supported
    if market_code not in ["NASD", "NYSE", "AMEX", "S&P"]:
        raise ValueError("Daytime orders are only supported for US markets")

    tr_id = "TTTS6036U" if order_type == "buy" else "TTTS6037U"

    ord_type = "00" if order_type == "buy" else "01"

    data = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "PDNO": symbol,
        "ORD_DVSN": ord_type,
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
        "EXCD": market_code,
        "ORD_SVR_DVSN_CD": "00",
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/daytime-order",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def cancel_overseas_daytime_order(
    client: Any,
    account_number: str,
    order_number: str,
    symbol: str,
    market_code: str,
    original_order_type: Literal["buy", "sell"],
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Cancel a daytime (intraday) order for US stocks.

    This function cancels a previously placed daytime order.
    Only available for US market stocks.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        order_number: Original order number to cancel.
        symbol: US stock symbol.
        market_code: Market code (must be US market).
        original_order_type: Original order type - 'buy' or 'sell'.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing cancellation confirmation.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = cancel_overseas_daytime_order(
        ...     client=client,
        ...     account_number="12345678",
        ...     order_number="0000001234",
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     original_order_type="buy",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-027
        - Real TR_ID: TTTS6038U
        - Paper TR_ID: Not Supported
        - Only available for US markets
        - URL: /uapi/overseas-stock/v1/trading/daytime-order-rvsecncl
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    if market_code not in ["NASD", "NYSE", "AMEX", "S&P"]:
        raise ValueError("Daytime orders are only supported for US markets")

    tr_id = "TTTS6038U"

    data = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "ODNO": order_number,
        "PDNO": symbol,
        "ORD_DVSN": "00" if original_order_type == "buy" else "01",
        "EXCD": market_code,
        "RVSE_CNCL_DVSN_CD": "02",
    }

    return client.make_request(
        method="POST",
        path="/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def get_overseas_period_profit(
    client: Any,
    account_number: str,
    market_code: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get period profit/loss for overseas stock trading.

    This function retrieves profit and loss information for overseas stock
    trading activities during the specified period.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing profit/loss data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_period_profit(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     start_date="20240101",
        ...     end_date="20240131",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-032
        - Real TR_ID: TTTS3039R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/inquire-period-profit
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "TTTS3039R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,
        "STRT_DT": start_date,
        "END_DT": end_date,
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-period-profit",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_margin_info(
    client: Any,
    account_number: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas margin information by currency.

    This function retrieves margin information for overseas trading
    broken down by currency.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing margin information by currency.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_margin_info(
        ...     client=client,
        ...     account_number="12345678",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-035
        - Real TR_ID: TTTC2101R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/foreign-margin
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "TTTC2101R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/foreign-margin",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_daily_transactions(
    client: Any,
    account_number: str,
    market_code: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get daily transaction history for overseas stocks.

    This function retrieves detailed daily transaction records for overseas
    stock trading activities.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing daily transaction data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_daily_transactions(
        ...     client=client,
        ...     account_number="12345678",
        ...     market_code="NASD",
        ...     start_date="20240101",
        ...     end_date="20240131",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-063
        - Real TR_ID: CTOS4001R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/inquire-period-trans
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTOS4001R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "EXCD": market_code,
        "STRT_DT": start_date,
        "END_DT": end_date,
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-period-trans",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_payment_balance(
    client: Any,
    account_number: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stock balance based on payment/settlement standard.

    This function retrieves account balance information calculated based on
    payment/settlement standards.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing payment-based balance information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_payment_balance(
        ...     client=client,
        ...     account_number="12345678",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-064
        - Real TR_ID: CTRP6010R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTRP6010R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_algo_conclusion(
    client: Any,
    account_number: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get conclusion history for designated price orders (algo orders).

    This function retrieves the execution history for algorithmic/designated
    price orders placed on overseas stocks.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing algo order conclusion data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_algo_conclusion(
        ...     client=client,
        ...     account_number="12345678",
        ...     start_date="20240101",
        ...     end_date="20240131",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-070
        - Real TR_ID: TTTS6059R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/inquire-algo-ccnl
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "TTTS6059R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
        "STRT_DT": start_date,
        "END_DT": end_date,
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/inquire-algo-ccnl",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_algo_order_number(
    client: Any,
    account_number: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get designated price order (algo order) numbers.

    This function retrieves the list of algorithmic/designated price order
    numbers for the account.

    Args:
        client: KISRestClient instance for making API requests.
        account_number: Account number (8 digits).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing algo order number list.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_algo_order_number(
        ...     client=client,
        ...     account_number="12345678",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-071
        - Real TR_ID: TTTS6058R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/trading/algo-ordno
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "TTTS6058R"

    params = {
        "CANO": account_number[:8],
        "ACNT_PRDT_CD": "01",
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/trading/algo-ordno",
        params=params,
        headers={"tr_id": tr_id},
    )


# URL constants for reference
OVERSEAS_TRADING_BASE_PATH = "/uapi/overseas-stock/v1/trading"


def get_overseas_order_api_url(endpoint: str) -> str:
    """
    Get the full URL for an overseas stock order API endpoint.

    Args:
        endpoint: The API endpoint path.

    Returns:
        str: The complete URL path for the specified endpoint.

    Examples:
        >>> url = get_overseas_order_api_url("/order")
        >>> print(url)
        /uapi/overseas-stock/v1/trading/order
    """
    return f"{OVERSEAS_TRADING_BASE_PATH}{endpoint}"
