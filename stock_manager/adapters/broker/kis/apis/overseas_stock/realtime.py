"""
KIS (Korea Investment & Securities) Overseas Stock Real-time API Functions.

This module provides functions for accessing real-time overseas stock data
including price quotes, asking prices, and contract notifications.

API Reference: https://apiportal.koreainvestment.com/
"""

from typing import Any, Dict


def get_overseas_delayed_price(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get delayed real-time price for overseas stocks.

    This function retrieves delayed real-time price information for overseas stocks.
    Note: This is a delayed data service, not truly real-time.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing delayed price information including:
            - Current price
            - Bid/ask prices
            - Trading volume
            - Price change

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_delayed_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 실시간-007
        - Real TR_ID: HDFSCNT0
        - Paper TR_ID: Not Supported
        - URL: /tryitout/HDFSCNT0
        - This is a WebSocket-based service
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HDFSCNT0"

    data = {
        "symbol": symbol,
        "excd": market_code,
    }

    return client.make_request(
        method="POST",
        path="/tryitout/HDFSCNT0",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def get_overseas_asking_price_realtime(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get real-time asking price (bid/ask) for Asian overseas stocks.

    This function retrieves real-time bid and ask prices for Asian market stocks.
    Note: This service is specifically for Asian markets.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., '7203' for Toyota).
        market_code: Asian market code (e.g., 'TKSE' for Tokyo, 'SHAI' for Shanghai).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing real-time bid/ask information including:
            - Bid prices
            - Ask prices
            - Bid/ask sizes
            - Spread information

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_asking_price_realtime(
        ...     client=client,
        ...     symbol="7203",
        ...     market_code="TKSE",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 실시간-008
        - Real TR_ID: HDFSASP1
        - Paper TR_ID: Not Supported
        - URL: /tryitout/HDFSASP1
        - Only available for Asian markets (Japan, China, Hong Kong, Vietnam)
        - This is a WebSocket-based service
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HDFSASP1"

    data = {
        "symbol": symbol,
        "excd": market_code,
    }

    return client.make_request(
        method="POST",
        path="/tryitout/HDFSASP1",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def get_overseas_realtime_conclusion(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get real-time contract (execution) notifications for overseas stocks.

    This function subscribes to real-time execution notifications for overseas
    stocks, providing immediate updates when trades are executed.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing real-time execution data including:
            - Execution price
            - Execution quantity
            - Execution time
            - Buy/sell indicator

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_realtime_conclusion(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=True
        ... )

    Notes:
        - API ID: 실시간-009
        - Real TR_ID: H0GSCNI0
        - Paper TR_ID: H0GSCNI9
        - URL: /tryitout/H0GSCNI0
        - This is a WebSocket-based service
        - Requires WebSocket approval key for connection
    """
    tr_id = "H0GSCNI9" if is_paper_trading else "H0GSCNI0"

    data = {
        "symbol": symbol,
        "excd": market_code,
    }

    return client.make_request(
        method="POST",
        path="/tryitout/H0GSCNI0",
        json_data=data,
        headers={"tr_id": tr_id},
    )


def get_overseas_realtime_asking_price(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get real-time asking price (bid/ask) for overseas stocks.

    This function retrieves real-time bid and ask prices for overseas stocks
    with live order book information.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing real-time bid/ask information including:
            - Multiple bid levels with prices and sizes
            - Multiple ask levels with prices and sizes
            - Best bid and ask
            - Spread information
            - Order book depth

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_realtime_asking_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 실시간-021
        - Real TR_ID: HDFSASP0
        - Paper TR_ID: Not Supported
        - URL: /tryitout/HDFSASP0
        - This is a WebSocket-based service
        - Requires WebSocket approval key for connection
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HDFSASP0"

    data = {
        "symbol": symbol,
        "excd": market_code,
    }

    return client.make_request(
        method="POST",
        path="/tryitout/HDFSASP0",
        json_data=data,
        headers={"tr_id": tr_id},
    )


# WebSocket helper functions

def get_websocket_approval_key(
    client: Any,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get approval key for WebSocket connection.

    This function retrieves an approval key required for establishing a
    WebSocket connection to receive real-time overseas stock data.

    Args:
        client: KISRestClient instance for making API requests.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing:
            - approval_key (str): WebSocket approval key
            - rt_cd (str): Return code
            - msg_cd (str): Message code
            - msg1 (str): Message description

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_websocket_approval_key(
        ...     client=client,
        ...     is_paper_trading=True
        ... )
        >>> approval_key = response.get("approval_key")

    Notes:
        - The approval key has a limited validity period
        - A new approval key is required for each WebSocket connection
        - Use the approve_websocket_key function from oauth module for detailed implementation
    """
    from stock_manager.adapters.broker.kis.apis.oauth.oauth import approve_websocket_key

    return approve_websocket_key(
        app_key=client.config.app_key.get_secret_value(),
        app_secret=client.config.app_secret.get_secret_value(),
        access_token=client.state.access_token.access_token if client.state.access_token else "",
        is_paper_trading=is_paper_trading,
    )


# URL constants for reference
OVERSEAS_REALTIME_BASE_PATH = "/tryitout"


def get_overseas_realtime_api_url(endpoint: str) -> str:
    """
    Get the full URL for an overseas stock real-time API endpoint.

    Args:
        endpoint: The API endpoint path.

    Returns:
        str: The complete URL path for the specified endpoint.

    Examples:
        >>> url = get_overseas_realtime_api_url("/H0GSCNI0")
        >>> print(url)
        /tryitout/H0GSCNI0
    """
    return f"{OVERSEAS_REALTIME_BASE_PATH}{endpoint}"


# Real-time TR_ID constants for reference
OVERSEAS_REALTIME_TR_IDS = {
    "delayed_price": {
        "real": "HDFSCNT0",
        "paper": None,
    },
    "asking_price_asia": {
        "real": "HDFSASP1",
        "paper": None,
    },
    "realtime_conclusion": {
        "real": "H0GSCNI0",
        "paper": "H0GSCNI9",
    },
    "realtime_asking_price": {
        "real": "HDFSASP0",
        "paper": None,
    },
}


def get_realtime_tr_id(
    service_name: str,
    is_paper_trading: bool = False,
) -> str:
    """
    Get the appropriate TR_ID for a real-time service.

    Args:
        service_name: Name of the real-time service.
            Options: 'delayed_price', 'asking_price_asia', 'realtime_conclusion',
                    'realtime_asking_price'
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to False for real trading.

    Returns:
        str: The TR_ID for the specified service and trading mode.

    Raises:
        ValueError: If service_name is invalid or paper trading not supported.

    Examples:
        >>> tr_id = get_realtime_tr_id("realtime_conclusion", is_paper_trading=True)
        >>> print(tr_id)
        H0GSCNI9

    Notes:
        - Many real-time services do not support paper trading
        - Check OVERSEAS_REALTIME_TR_IDS for supported services
    """
    if service_name not in OVERSEAS_REALTIME_TR_IDS:
        raise ValueError(
            f"Invalid service_name: {service_name}. "
            f"Valid options: {list(OVERSEAS_REALTIME_TR_IDS.keys())}"
        )

    tr_id_info = OVERSEAS_REALTIME_TR_IDS[service_name]
    tr_id = tr_id_info["paper"] if is_paper_trading else tr_id_info["real"]

    if tr_id is None:
        raise ValueError(
            f"Paper trading is not supported for {service_name}. "
            "Use is_paper_trading=False."
        )

    return tr_id
