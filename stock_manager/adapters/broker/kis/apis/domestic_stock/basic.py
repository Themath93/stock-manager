"""
Domestic Stock Basic APIs for KIS (Korea Investment Securities) OpenAPI.

This module provides functions to query domestic stock basic price information
including current prices, daily prices, intraday data, investor trading data,
and ETF/ETN related information.

TR_ID Reference:
- Real Trading: Production environment TR_IDs
- Paper Trading: Simulation environment TR_IDs (where supported)
"""

from typing import Any, Dict, TypedDict

# API Endpoints
_BASE_URL = "https://api.koreainvestment.com"
_DOMESTIC_STOCK_BASE = "/uapi/domestic-stock/v1/quotations"
_ETNETN_BASE = "/uapi/etfetn/v1/quotations"


class _DomesticStockTrId(TypedDict):
    real: str
    paper: str | None


# TR_ID Constants
TR_IDS: dict[str, _DomesticStockTrId] = {
    # Both real and paper trading supported
    "v1_국내주식-008": {"real": "FHKST01010100", "paper": "FHKST01010100"},  # Current price
    "v1_국내주식-009": {"real": "FHKST01010300", "paper": "FHKST01010300"},  # Conclusion
    "v1_국내주식-010": {"real": "FHKST01010400", "paper": "FHKST01010400"},  # Daily price
    "v1_국내주식-011": {"real": "FHKST01010200", "paper": "FHKST01010200"},  # Ask/Bid
    "v1_국내주식-012": {"real": "FHKST01010900", "paper": "FHKST01010900"},  # Investor
    "v1_국내주식-013": {"real": "FHKST01010600", "paper": "FHKST01010600"},  # Member
    "v1_국내주식-016": {"real": "FHKST03010100", "paper": "FHKST03010100"},  # Period price
    "v1_국내주식-022": {"real": "FHKST03010200", "paper": "FHKST03010200"},  # Intraday chart
    "v1_국내주식-023": {"real": "FHPST01060000", "paper": "FHPST01060000"},  # Time conclusion
    "v1_국내주식-025": {
        "real": "FHPST02310000",
        "paper": "FHPST02310000",
    },  # Overtime time conclusion
    "v1_국내주식-026": {"real": "FHPST02320000", "paper": "FHPST02320000"},  # Overtime daily price
    # Real trading only (paper trading not supported)
    "v1_국내주식-054": {"real": "FHPST01010000", "paper": None},  # Price 2
    "v1_국내주식-068": {"real": "FHPST02400000", "paper": None},  # ETF/ETN price
    "v1_국내주식-069": {"real": "FHPST02440000", "paper": None},  # NAV comparison (item)
    "v1_국내주식-070": {"real": "FHPST02440100", "paper": None},  # NAV comparison (minute)
    "v1_국내주식-071": {"real": "FHPST02440200", "paper": None},  # NAV comparison (daily)
    "국내주식-073": {"real": "FHKST121600C0", "paper": None},  # ETF component
    "국내주식-076": {"real": "FHPST02300000", "paper": None},  # Overtime price
    "국내주식-077": {"real": "FHPST02300400", "paper": None},  # Overtime ask/bid
    "국내주식-120": {"real": "FHKST117300C0", "paper": None},  # Expected closing
    "국내주식-213": {"real": "FHKST03010230", "paper": None},  # Daily chart price
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-008')
        is_paper_trading: Whether to use paper trading TR_ID

    Returns:
        The TR_ID string for the specified environment

    Raises:
        ValueError: If the API_ID is not found or paper trading is not supported
    """
    if api_id not in TR_IDS:
        raise ValueError(f"Unknown API_ID: {api_id}")

    tr_id_info = TR_IDS[api_id]

    if is_paper_trading:
        paper_tr_id = tr_id_info["paper"]
        if paper_tr_id is None:
            raise ValueError(f"Paper trading is not supported for {api_id}")
        return paper_tr_id

    return tr_id_info["real"]


def inquire_current_price(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve current stock price information for domestic stocks.

    API ID: v1_국내주식-008
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-price
    TR_ID: FHKST01010100 (Real), FHKST01010100 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code (e.g., '005930' for Samsung Electronics)
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_cond_mrkt_div_code: Market division code (default: 'J')
            - fid_input_iscd: Issue code (stock_code)

    Returns:
        Dictionary containing:
            - rt_cd: Return code ('0' for success)
            - msg_cd: Message code
            - msg1: Message description
            - output: Current price data including:
                - stck_prpr: Current price
                - stck_oprc: Opening price
                - stck_hgpr: Highest price
                - stck_lwpr: Lowest price
                - acml_vol: Accumulated volume
                - acml_tr_pbmn: Accumulated trading amount
                - prdy_vrss: Price change from previous close
                - prdy_vrss_sign: Price change sign (1: up, 2: down, 3: unchanged)
                - prdy_ctrt: Price change rate

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> from stock_manager.adapters.broker.kis import KISRestClient
        >>> client = KISRestClient(config)
        >>> result = inquire_current_price(client, '005930')
        >>> if result['rt_cd'] == '0':
        ...     price = result['output']['stck_prpr']
        ...     print(f"Samsung Electronics current price: {price}")
    """
    api_id = "v1_국내주식-008"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_conclusion(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve current stock conclusion (trade execution) information.

    API ID: v1_국내주식-009
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-ccnl
    TR_ID: FHKST01010300 (Real), FHKST01010300 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing conclusion data including:
            - stck_prpr: Current price
            - prdy_vrss: Price change
            - prdy_ctrt: Price change rate
            - stck_vol: Current volume
            - stck_msrm: Trading amount (in millions)

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_conclusion(client, '005930')
        >>> if result['rt_cd'] == '0':
        ...     volume = result['output']['stck_vol']
        ...     print(f"Trading volume: {volume}")
    """
    api_id = "v1_국내주식-009"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-ccnl"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_daily_price(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily stock price information (historical data).

    API ID: v1_국내주식-010
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-price
    TR_ID: FHKST01010400 (Real), FHKST01010400 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_org_adj_prc: Adjusted price flag (1: adjusted, 0: unadjusted)
            - fid_div_clss_code: Classification code (default: '0')
            - fid_input_date_1: Start date (YYYYMMDD format)
            - fid_input_date_2: End date (YYYYMMDD format)
            - fid_period_div_code: Period division code (D: day, W: week, M: month, Y: year)

    Returns:
        Dictionary containing daily price data with output array of:
            - stck_bsop_date: Business date
            - stck_oprc: Opening price
            - stck_hgpr: Highest price
            - stck_lwpr: Lowest price
            - stck_clpr: Closing price
            - acml_vol: Accumulated volume
            - acml_tr_pbmn: Accumulated trading amount

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_daily_price(
        ...     client,
        ...     '005930',
        ...     fid_period_div_code='D',
        ...     fid_org_adj_prc='1'
        ... )
        >>> for day in result['output']:
        ...     print(f"{day['stck_bsop_date']}: {day['stck_clpr']}")
    """
    api_id = "v1_국내주식-010"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-daily-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
        "fid_org_adj_prc": kwargs.get("fid_org_adj_prc", "1"),
        "fid_div_clss_code": kwargs.get("fid_div_clss_code", "0"),
        "fid_input_date_1": kwargs.get("fid_input_date_1"),
        "fid_input_date_2": kwargs.get("fid_input_date_2"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", "D"),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_asking_price_expected_ccnl(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve asking price (bid/ask) and expected conclusion information.

    API ID: v1_국내주식-011
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn
    TR_ID: FHKST01010200 (Real), FHKST01010200 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing asking price data with:
            - bid prices: Total 10 buy orders (bid and quantity)
            - ask prices: Total 10 sell orders (ask and quantity)
            - Expected conclusion price and rate

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_asking_price_expected_ccnl(client, '005930')
        >>> output = result['output']
        >>> print(f"Bid 1: {output['bidp1']} / Ask 1: {output['askp1']}")
    """
    api_id = "v1_국내주식-011"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-asking-price-exp-ccn"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_investor(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve investor trading data by investor type (institutional, individual, foreign).

    API ID: v1_국내주식-012
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-investor
    TR_ID: FHKST01010900 (Real), FHKST01010900 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_div_clss_code: Classification code (default: '0')
            - fid_input_iscd: Issue code
            - fid_tr_dt: Trading date (YYYYMMDD format)

    Returns:
        Dictionary containing investor trading data:
            - Selling/buying amounts by investor type
            - Institutions: trust, bank, insurance, etc.
            - Foreign investors
            - Individual investors
            - Government

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_investor(client, '005930')
        >>> output = result['output']
        >>> print(f"Foreign buying: {output['frin_nttr_quan']}")
        >>> print(f"Individual selling: {output['psns_nttr_quan']}")
    """
    api_id = "v1_국내주식-012"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-investor"

    params = {
        "fid_div_clss_code": kwargs.get("fid_div_clss_code", "0"),
        "fid_input_iscd": stock_code,
        "fid_tr_dt": kwargs.get("fid_tr_dt"),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_member(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    retrieve member company trading data (by securities firm).

    API ID: v1_국내주식-013
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-member
    TR_ID: FHKST01010600 (Real), FHKST01010600 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_org_adj_prc: Adjusted price flag
            - fid_div_clss_code: Classification code
            - fid_cond_mrkt_div_code: Market division code
            - fid_input_iscd: Issue code
            - fid_tr_dt: Trading date (YYYYMMDD format)

    Returns:
        Dictionary containing member trading data:
            - Trading amounts by securities firm
            - Top 10 buying firms
            - Top 10 selling firms

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_member(client, '005930')
        >>> output = result['output']
        >>> print(f"Top buyer: {output.get('mb1_nm')}")
    """
    api_id = "v1_국내주식-013"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-member"

    params = {
        "fid_org_adj_prc": kwargs.get("fid_org_adj_prc", "1"),
        "fid_div_clss_code": kwargs.get("fid_div_clss_code", "0"),
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
        "fid_tr_dt": kwargs.get("fid_tr_dt"),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_period_price(
    client: Any,
    stock_code: str,
    period_code: str = "D",
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve periodic stock price data (daily/weekly/monthly/yearly).

    API ID: v1_국내주식-016
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
    TR_ID: FHKST03010100 (Real), FHKST03010100 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        period_code: Period division code - 'D' (daily), 'W' (weekly),
                     'M' (monthly), 'Y' (yearly) (default: 'D')
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_org_adj_prc: Adjusted price flag (1: adjusted, 0: unadjusted)
            - fid_input_iscd: Issue code
            - fid_input_date_1: Start date (YYYYMMDD format)
            - fid_input_date_2: End date (YYYYMMDD format)
            - fid_period_div_code: Period division code (overrides period_code)

    Returns:
        Dictionary containing historical price data:
            - Array of price data for each period
            - OHLC (Open, High, Low, Close) prices
            - Volume and trading amount

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> # Get weekly prices for Samsung
        >>> result = inquire_period_price(
        ...     client,
        ...     '005930',
        ...     period_code='W',
        ...     fid_org_adj_prc='1'
        ... )
        >>> for week in result['output']:
        ...     print(f"{week['stck_bsop_date']}: {week['stck_clpr']}")
    """
    api_id = "v1_국내주식-016"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-daily-itemchartprice"

    params = {
        "fid_org_adj_prc": kwargs.get("fid_org_adj_prc", "1"),
        "fid_input_iscd": stock_code,
        "fid_input_date_1": kwargs.get("fid_input_date_1"),
        "fid_input_date_2": kwargs.get("fid_input_date_2"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", period_code),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_intraday_chart(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve intraday minute-by-minute chart data for the current day.

    API ID: v1_국내주식-022
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice
    TR_ID: FHKST03010200 (Real), FHKST03010200 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code
            - fid_period_div_code: Time division code (default: '1' for 1-minute)
            - fid_mrkt_clss_code: Market classification code

    Returns:
        Dictionary containing intraday minute data:
            - Array of data for each time interval
            - Price, volume, and trading amount per minute

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_intraday_chart(client, '005930')
        >>> for minute in result['output']:
        ...     print(f"{minute['stck_prpr']} at {minute['stck_cntg_hour']}")
    """
    api_id = "v1_국내주식-022"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-time-itemchartprice"

    params = {
        "fid_input_iscd": stock_code,
        "fid_period_div_code": kwargs.get("fid_period_div_code", "1"),
        "fid_mrkt_clss_code": kwargs.get("fid_mrkt_clss_code", "J"),
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_time_itemconclusion(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve time-series trading conclusion data for the current day.

    API ID: v1_국내주식-023
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion
    TR_ID: FHPST01060000 (Real), FHPST01060000 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing time-series conclusion data:
            - Hourly trading data
            - Cumulative volume and price per time segment

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_time_itemconclusion(client, '005930')
        >>> for period in result['output']:
        ...     print(f"Hour {period['cntg_hour']}: {period['stck_prpr']}")
    """
    api_id = "v1_국내주식-023"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-time-itemconclusion"

    params = {
        "fid_input_iscd": stock_code,
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_overtime_conclusion(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve after-hours trading conclusion data by time.

    API ID: v1_국내주식-025
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion
    TR_ID: FHPST02310000 (Real), FHPST02310000 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing after-hours time-series conclusion data:
            - Time-segmented trading data
            - Volume and price during after-hours session

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_overtime_conclusion(client, '005930')
        >>> for period in result['output']:
        ...     print(f"Time {period['cntg_hour']}: {period['stck_prpr']}")
    """
    api_id = "v1_국내주식-025"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-time-overtimeconclusion"

    params = {
        "fid_input_iscd": stock_code,
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_overtime_daily_price(
    client: Any,
    stock_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily after-hours trading price data.

    API ID: v1_국내주식-026
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice
    TR_ID: FHPST02320000 (Real), FHPST02320000 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_org_adj_prc: Adjusted price flag
            - fid_div_clss_code: Classification code
            - fid_input_date_1: Start date (YYYYMMDD format)
            - fid_input_date_2: End date (YYYYMMDD format)
            - fid_period_div_code: Period division code

    Returns:
        Dictionary containing after-hours daily price data:
            - Array of daily after-hours OHLC data
            - Volume and trading amount

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_overtime_daily_price(client, '005930')
        >>> for day in result['output']:
        ...     print(f"{day['stck_bsop_date']}: {day['stck_clpr']}")
    """
    api_id = "v1_국내주식-026"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-daily-overtimeprice"

    params = {
        "fid_org_adj_prc": kwargs.get("fid_org_adj_prc", "1"),
        "fid_div_clss_code": kwargs.get("fid_div_clss_code", "0"),
        "fid_input_iscd": stock_code,
        "fid_input_date_1": kwargs.get("fid_input_date_1"),
        "fid_input_date_2": kwargs.get("fid_input_date_2"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", "D"),
    }

    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_price_2(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve alternative current stock price information (Real trading only).

    API ID: v1_국내주식-054
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-price-2
    TR_ID: FHPST01010000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing alternative price data format with additional fields

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_price_2(client, '005930')
        >>> if result['rt_cd'] == '0':
        ...     print(f"Price: {result['output']['stck_prpr']}")
    """
    api_id = "v1_국내주식-054"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-price-2"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_etfetn_price(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve current price for ETF/ETN securities (Real trading only).

    API ID: v1_국내주식-068
    Endpoint: /uapi/etfetn/v1/quotations/inquire-price
    TR_ID: FHPST02400000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit ETF/ETN code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ETF/ETN price data:
            - Current market price
            - NAV (Net Asset Value)
            - Premium/Discount rate
            - Trading volume and amount

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_etfetn_price(client, '069500')  # KODEX 200
        >>> output = result['output']
        >>> print(f"NAV: {output['nav']}")
        >>> print(f"Premium rate: {output['prvs_rate']}")
    """
    api_id = "v1_국내주식-068"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ETNETN_BASE}/inquire-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_nav_comparison_trend(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve NAV comparison trend data for ETF/ETN by item (Real trading only).

    API ID: v1_국내주식-069
    Endpoint: /uapi/etfetn/v1/quotations/nav-comparison-trend
    TR_ID: FHPST02440000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit ETF/ETN code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing NAV comparison data:
            - Historical NAV vs market price
            - Premium/Discount trends

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_nav_comparison_trend(client, '069500')
        >>> for data in result['output']:
        ...     print(f"NAV: {data['nav']}, Price: {data['stck_prpr']}")
    """
    api_id = "v1_국내주식-069"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ETNETN_BASE}/nav-comparison-trend"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_nav_comparison_time_trend(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve NAV comparison trend by minute (Real trading only).

    API ID: v1_국내주식-070
    Endpoint: /uapi/etfetn/v1/quotations/nav-comparison-time-trend
    TR_ID: FHPST02440100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit ETF/ETN code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing minute-by-minute NAV comparison data

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_nav_comparison_time_trend(client, '069500')
        >>> for minute in result['output']:
        ...     print(f"Time {minute['cntg_hour']}: NAV {minute['nav']}")
    """
    api_id = "v1_국내주식-070"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ETNETN_BASE}/nav-comparison-time-trend"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_nav_comparison_daily_trend(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve NAV comparison trend by day (Real trading only).

    API ID: v1_국내주식-071
    Endpoint: /uapi/etfetn/v1/quotations/nav-comparison-daily-trend
    TR_ID: FHPST02440200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit ETF/ETN code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing daily NAV comparison data:
            - Daily NAV vs market price
            - Premium/Discount trends

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_nav_comparison_daily_trend(client, '069500')
        >>> for day in result['output']:
        ...     print(f"{day['bass_dt']}: NAV {day['nav']}")
    """
    api_id = "v1_국내주식-071"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ETNETN_BASE}/nav-comparison-daily-trend"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_etf_component_price(
    client: Any,
    etf_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve constituent stock prices of an ETF (Real trading only).

    API ID: 국내주식-073
    Endpoint: /uapi/etfetn/v1/quotations/inquire-component-stock-price
    TR_ID: FHKST121600C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        etf_code: 6-digit ETF code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ETF component stock prices:
            - Constituent stock list
            - Each stock's current price and quantity
            - Weight in the ETF portfolio

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_etf_component_price(client, '069500')
        >>> for stock in result['output']:
        ...     print(f"{stock['name']}: {stock['stck_prpr']}, Qty: {stock['quant']}")
    """
    api_id = "국내주식-073"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ETNETN_BASE}/inquire-component-stock-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": etf_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_overtime_price(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve after-hours current price information (Real trading only).

    API ID: 국내주식-076
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-overtime-price
    TR_ID: FHPST02300000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing after-hours price data:
            - Current after-hours price
            - Volume during after-hours session
            - Trading amount

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_overtime_price(client, '005930')
        >>> output = result['output']
        >>> print(f"After-hours price: {output['stck_prpr']}")
    """
    api_id = "국내주식-076"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-overtime-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_overtime_asking_price(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve after-hours asking price (bid/ask) information (Real trading only).

    API ID: 국내주식-077
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price
    TR_ID: FHPST02300400 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing after-hours bid/ask data:
            - Buy and sell orders during after-hours
            - Order quantities

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_overtime_asking_price(client, '005930')
        >>> output = result['output']
        >>> print(f"Bid: {output['bidp1']}, Ask: {output['askp1']}")
    """
    api_id = "국내주식-077"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-overtime-asking-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_expected_closing_price(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve expected closing price at market close (Real trading only).

    API ID: 국내주식-120
    Endpoint: /uapi/domestic-stock/v1/quotations/exp-closing-price
    TR_ID: FHKST117300C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        **kwargs: Additional parameters

    Returns:
        Dictionary containing expected closing price data:
            - Predicted closing price
            - Expected settlement price

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_expected_closing_price(client, '005930')
        >>> output = result['output']
        >>> print(f"Expected closing: {output['exp_prpr']}")
    """
    api_id = "국내주식-120"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/exp-closing-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": stock_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def inquire_daily_chart_price(
    client: Any,
    stock_code: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily minute chart price data (Real trading only).

    API ID: 국내주식-213
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice
    TR_ID: FHKST03010230 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        stock_code: 6-digit stock code
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code
            - fid_period_div_code: Time division code
            - fid_mrkt_clss_code: Market classification code

    Returns:
        Dictionary containing daily minute chart data:
            - Intraday price movements
            - Volume per minute

    Raises:
        ValueError: If invalid parameters are provided or paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_daily_chart_price(client, '005930')
        >>> for minute in result['output']:
        ...     print(f"{minute['stck_prpr']} at {minute['stck_cntg_hour']}")
    """
    api_id = "국내주식-213"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-time-dailychartprice"

    params = {
        "fid_input_iscd": stock_code,
        "fid_period_div_code": kwargs.get("fid_period_div_code", "1"),
        "fid_mrkt_clss_code": kwargs.get("fid_mrkt_clss_code", "J"),
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )
