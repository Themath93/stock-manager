"""
KIS (Korea Investment & Securities) Overseas Stock Basic Price API Functions.

This module provides functions for accessing overseas stock basic price information
including current prices, daily prices, time-series data, and market information.

API Reference: https://apiportal.koreainvestment.com/
"""

from typing import Any, Dict, Literal


def get_overseas_current_price(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get the current price of an overseas stock.

    This function retrieves the current trading price for an overseas stock
    including real-time price information, bid/ask prices, and trading volume.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description
            - output (dict): Current price data including:
                - sym (str): Symbol
                - last (str): Last price
                - diff (str): Price change
                - rate (str): Change rate
                - volume (str): Trading volume

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> from stock_manager.adapters.broker.kis import KISRestClient
        >>> client = KISRestClient(config)
        >>> client.authenticate()
        >>> response = get_overseas_current_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=True
        ... )
        >>> print(response["output"]["last"])

    Notes:
        - API ID: v1_해외주식-009
        - Real TR_ID: HHDFS00000300
        - Paper TR_ID: HHDFS00000300
        - URL: /uapi/overseas-price/v1/quotations/price
    """
    tr_id = "HHDFS00000300"  # Same for both real and paper

    params = {
        "AUTH": "",  # Server authorization
        "EXCD": market_code,  # Exchange code
        "SYMB": symbol,  # Symbol
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/price",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_daily_price(
    client: Any,
    symbol: str,
    market_code: str,
    period_code: Literal["D", "W", "M"] = "D",
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get daily/weekly/monthly price data for an overseas stock.

    This function retrieves historical price data for an overseas stock
    for specified time periods (daily, weekly, or monthly).

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        period_code: Time period code.
            'D' for daily, 'W' for weekly, 'M' for monthly.
            Defaults to 'D' (daily).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing:
            - rt_cd (str): Return code ('0' for success, '1' for failure)
            - msg_cd (str): Message code
            - msg1 (str): Message description
            - output (dict): Array of daily price data including:
                - stdd (str): Standard date
                - openp (str): Open price
                - highp (str): High price
                - lowp (str): Low price
                - closp (str): Close price
                - volume (str): Trading volume

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_daily_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     period_code="D"
        ... )
        >>> for day_data in response["output"]:
        ...     print(f"{day_data['stdd']}: {day_data['closp']}")

    Notes:
        - API ID: v1_해외주식-010
        - Real TR_ID: HHDFS76240000
        - Paper TR_ID: HHDFS76240000
        - URL: /uapi/overseas-price/v1/quotations/dailyprice
    """
    tr_id = "HHDFS76240000"  # Same for both real and paper

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
        "GUBN": period_code,  # D: daily, W: weekly, M: monthly
        "BYMD": "",  # Inquiry end date (YYYYMMDD)
        "MODP": "0",  # 0: from specified date backwards, 1: from specified date forwards
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/dailyprice",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_daily_chart_price(
    client: Any,
    symbol: str,
    market_code: str,
    period_code: Literal["D", "W", "M", "Y"] = "D",
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Get daily/weekly/monthly/yearly chart price data for overseas stock/index/exchange rate.

    This function retrieves comprehensive chart price data for overseas stocks,
    indices, or exchange rates with customizable time periods.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol, index code, or currency code.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'AMD').
        period_code: Time period code.
            'D' for daily, 'W' for weekly, 'M' for monthly, 'Y' for yearly.
            Defaults to 'D' (daily).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing chart price data with OHLCV values.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_daily_chart_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     period_code="D"
        ... )

    Notes:
        - API ID: v1_해외주식-012
        - Real TR_ID: FHKST03030100
        - Paper TR_ID: FHKST03030100
        - URL: /uapi/overseas-price/v1/quotations/inquire-daily-chartprice
    """
    tr_id = "FHKST03030100"  # Same for both real and paper

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
        "FID_INPUT_ISCD": symbol,
        "FID_PERIOD_COND_CODE": period_code,  # D, W, M, Y
        "FID_ORIG_ADJ_PRC": "0000000000",  # Request for adjusted price
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
        params=params,
        headers={"tr_id": tr_id},
    )


def search_overseas_stocks(
    client: Any,
    market_code: str,
    search_type: Literal["0", "1", "2"] = "0",
    is_paper_trading: bool = True,
) -> Dict[str, Any]:
    """
    Search for overseas stocks by market code.

    This function retrieves a list of overseas stocks based on market code
    and search criteria.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        search_type: Search type code.
            '0' for all, '1' for Kosdaq, '2' for Kospi.
            Defaults to '0' (all).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        Dict[str, Any]: API response containing list of stocks matching criteria.

    Raises:
        ValueError: If required parameters are invalid.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = search_overseas_stocks(
        ...     client=client,
        ...     market_code="NASD",
        ...     search_type="0"
        ... )

    Notes:
        - API ID: v1_해외주식-015
        - Real TR_ID: HHDFS76410000
        - Paper TR_ID: HHDFS76410000
        - URL: /uapi/overseas-price/v1/quotations/inquire-search
    """
    tr_id = "HHDFS76410000"  # Same for both real and paper

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "TYPE": search_type,  # 0: all, 1: Kosdaq, 2: Kospi
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-search",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_price_detail(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get detailed current price information for an overseas stock.

    This function retrieves comprehensive current price details including
    bid/ask prices, trading volume, and other trading information.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing detailed price information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_price_detail(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-029
        - Real TR_ID: HHDFS76200200
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/price-detail
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76200200"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/price-detail",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_time_item_chart(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get intraday (minute-by-minute) chart data for an overseas stock.

    This function retrieves detailed intraday price data showing price movements
    throughout the trading day.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing intraday chart data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_time_item_chart(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-030
        - Real TR_ID: HHDFS76950200
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/inquire-time-itemchartprice
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76950200"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_time_index_chart(
    client: Any,
    index_code: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get intraday (minute-by-minute) chart data for an overseas index.

    This function retrieves detailed intraday price data for overseas market indices.

    Args:
        client: KISRestClient instance for making API requests.
        index_code: Index code (e.g., 'DJI' for Dow Jones, 'IXIC' for NASDAQ).
        market_code: Market code for the index.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing intraday index chart data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_time_index_chart(
        ...     client=client,
        ...     index_code="DJI",
        ...     market_code="NYSE",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-031
        - Real TR_ID: FHKST03030200
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/inquire-time-indexchartprice
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "FHKST03030200"  # Real trading only

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
        "FID_INPUT_ISCD": index_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_product_info(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get basic product information for an overseas stock.

    This function retrieves fundamental information about an overseas stock
    including company details, listing information, and basic specifications.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing product information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_product_info(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: v1_해외주식-034
        - Real TR_ID: CTPF1702R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/search-info
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTPF1702R"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/search-info",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_settlement_date(
    client: Any,
    country_code: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get settlement dates (holidays) for overseas markets.

    This function retrieves information about settlement dates and holidays
    for overseas markets, which is important for trading schedule planning.

    Args:
        client: KISRestClient instance for making API requests.
        country_code: Country code (e.g., 'US' for United States, 'JP' for Japan).
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing settlement date information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_settlement_date(
        ...     client=client,
        ...     country_code="US",
        ...     start_date="20240101",
        ...     end_date="20241231",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-017
        - Real TR_ID: CTOS5011R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/quotations/countries-holiday
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTOS5011R"  # Real trading only

    params = {
        "AUTH": "",
        "CNTR": country_code,  # Country code
        "STDT": start_date,  # Start date (YYYYMMDD)
        "ENDT": end_date,  # End date (YYYYMMDD)
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/quotations/countries-holiday",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_asking_price(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get asking price (bid/ask) information for an overseas stock.

    This function retrieves current bid and ask prices with detailed
    order book information.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing bid/ask price information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_asking_price(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-033
        - Real TR_ID: HHDFS76200100
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/inquire-asking-price
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76200100"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-asking-price",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_conclusion_trend(
    client: Any,
    symbol: str,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get conclusion (execution) trend data for an overseas stock.

    This function retrieves recent trading execution trends showing buy/sell
    pressure and price movements.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        market_code: Market code (e.g., 'NASD' for NASDAQ, 'NYSE' for NYSE).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing conclusion trend data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_conclusion_trend(
        ...     client=client,
        ...     symbol="AAPL",
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-037
        - Real TR_ID: HHDFS76200300
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/inquire-ccnl
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76200300"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "SYMB": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/inquire-ccnl",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_industry_theme_price(
    client: Any,
    market_code: str,
    industry_group_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get price information for overseas industry sectors/themes.

    This function retrieves price data for specific industry sectors or themes
    in overseas markets.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE').
        industry_group_code: Industry group or theme code.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing industry/theme price data.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_industry_theme_price(
        ...     client=client,
        ...     market_code="NASD",
        ...     industry_group_code="TECH",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-048
        - Real TR_ID: HHDFS76370000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/industry-theme
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76370000"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
        "INDTP_GRP_CD": industry_group_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/industry-theme",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_industry_code(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get industry/sector codes for overseas markets.

    This function retrieves a list of industry/sector classification codes
    used in overseas markets.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing industry code information.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_industry_code(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-049
        - Real TR_ID: HHDFS76370100
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/industry-price
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76370100"  # Real trading only

    params = {
        "AUTH": "",
        "EXCD": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/industry-price",
        params=params,
        headers={"tr_id": tr_id},
    )


# URL constants for reference
OVERSEAS_PRICE_BASE_PATH = "/uapi/overseas-price/v1"
OVERSEAS_STOCK_BASE_PATH = "/uapi/overseas-stock/v1"


def get_overseas_basic_api_url(
    endpoint: str,
    is_paper_trading: bool = True,
) -> str:
    """
    Get the full URL for an overseas stock basic price API endpoint.

    Args:
        endpoint: The API endpoint path.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Defaults to True for paper trading environment.

    Returns:
        str: The complete URL path for the specified endpoint.

    Examples:
        >>> url = get_overseas_basic_api_url(
        ...     "/quotations/price",
        ...     is_paper_trading=True
        ... )
        >>> print(url)
        /uapi/overseas-price/v1/quotations/price
    """
    return f"{OVERSEAS_PRICE_BASE_PATH}{endpoint}"
