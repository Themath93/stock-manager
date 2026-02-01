"""
KIS (Korea Investment & Securities) Domestic Stock Sector API

This module provides functions for interacting with KIS OpenAPI domestic stock
sector and industry index endpoints.

APIs included:
- Industry index prices (daily, weekly, monthly, yearly)
- Industry index intraday data (minute, tick)
- Industry index current prices
- Volatility Interrupter (VI) status
- Market holidays and business days
- Expected settlement indices
- News and interest rates
"""

from typing import Any, Dict

# API Endpoints
_DOMESTIC_STOCK_BASE = "/uapi/domestic-stock/v1/quotations"

# TR_ID Constants
TR_IDS = {
    # Both real and paper trading supported
    "v1_국내주식-021": {"real": "FHKUP03500100", "paper": "FHKUP03500100"},  # Daily index chart price

    # Real trading only (paper trading not supported)
    "v1_국내주식-045": {"real": "FHKUP03500200", "paper": None},  # Time index chart price
    "v1_국내주식-055": {"real": "FHPST01390000", "paper": None},  # VI status
    "v1_국내주식-063": {"real": "FHPUP02100000", "paper": None},  # Index price
    "v1_국내주식-065": {"real": "FHPUP02120000", "paper": None},  # Index daily price
    "v1_국내주식-066": {"real": "FHPUP02140000", "paper": None},  # Index category price
    "국내주식-040": {"real": "CTCA0903R", "paper": None},         # Check holiday
    "국내주식-064": {"real": "FHPUP02110100", "paper": None},     # Index tick price
    "국내주식-119": {"real": "FHPUP02110200", "paper": None},     # Index time price
    "국내주식-121": {"real": "FHPST01840000", "paper": None},     # Expected index trend
    "국내주식-122": {"real": "FHKUP11750000", "paper": None},     # Expected total index
    "국내주식-141": {"real": "FHKST01011800", "paper": None},     # News title
    "국내주식-155": {"real": "FHPST07020000", "paper": None},     # Compare interest
    "국내주식-160": {"real": "HHMCM000002C0", "paper": None},     # Market time
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-021')
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
        if tr_id_info["paper"] is None:
            raise ValueError(f"Paper trading is not supported for {api_id}")
        return tr_id_info["paper"]

    return tr_id_info["real"]


def get_inquire_daily_indexchartprice(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock industry index period prices (daily/weekly/monthly/yearly).

    API ID: v1_국내주식-021
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice
    TR_ID: FHKUP03500100 (Real), FHKUP03500100 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code (e.g., '001' for KOSPI, '002' for industry sectors)
            - fid_period_div_code: Period division code (D: day, W: week, M: month, Y: year)
            - fid_input_date_1: Start date (YYYYMMDD format)
            - fid_input_date_2: End date (YYYYMMDD format)

    Returns:
        Dictionary containing:
            - rt_cd: Return code ('0' for success)
            - msg_cd: Message code
            - msg1: Message description
            - output: Index price data including:
                - Array of OHLC (Open, High, Low, Close) data
                - Volume and trading amount

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_daily_indexchartprice(
        ...     client,
        ...     fid_input_iscd='001',
        ...     fid_period_div_code='D'
        ... )
        >>> if result['rt_cd'] == '0':
        ...     for day in result['output']:
        ...         print(f"{day['stck_bsop_date']}: {day['idx_clpr']}")
    """
    api_id = "v1_국내주식-021"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-daily-indexchartprice"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", "D"),
        "fid_input_date_1": kwargs.get("fid_input_date_1"),
        "fid_input_date_2": kwargs.get("fid_input_date_2"),
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


def get_inquire_time_indexchartprice(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve industry index minute-by-minute chart data (Real trading only).

    API ID: v1_국내주식-045
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice
    TR_ID: FHKUP03500200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code
            - fid_period_div_code: Time division code

    Returns:
        Dictionary containing intraday minute data for industry indices

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_time_indexchartprice(
        ...     client,
        ...     fid_input_iscd='001'
        ... )
        >>> for minute in result['output']:
        ...     print(f"{minute['idx_prpr']} at {minute['cntg_hour']}")
    """
    api_id = "v1_국내주식-045"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-time-indexchartprice"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", "1"),
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


def get_inquire_vi_status(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve Volatility Interrupter (VI) status for domestic stocks (Real trading only).

    API ID: v1_국내주식-055
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-vi-status
    TR_ID: FHPST01390000 (Real only - Paper trading NOT supported)

    The VI (Volatility Interrupter) is a circuit breaker mechanism that temporarily
    halts trading when prices fluctuate excessively within a short period.

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters

    Returns:
        Dictionary containing VI status information:
            - Current VI status for stocks/indices
            - VI trigger prices and thresholds

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_vi_status(client)
        >>> if result['rt_cd'] == '0':
        ...     print(f"VI Status: {result['output']}")
    """
    api_id = "v1_국내주식-055"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-vi-status"

    params = {**kwargs}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_inquire_index_price(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve current industry index prices (Real trading only).

    API ID: v1_국내주식-063
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-index-price
    TR_ID: FHPUP02100000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code (e.g., '001' for KOSPI, '201' for KOSDAQ)

    Returns:
        Dictionary containing current index price data:
            - idx_prpr: Current index price
            - idx_oprc: Opening index price
            - idx_hgpr: Highest index price
            - idx_lwpr: Lowest index price
            - idx_vs: Volume

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_index_price(client, fid_input_iscd='001')
        >>> if result['rt_cd'] == '0':
        ...     print(f"KOSPI: {result['output']['idx_prpr']}")
    """
    api_id = "v1_국내주식-063"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-index-price"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
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


def get_inquire_index_daily_price(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve industry index daily prices (Real trading only).

    API ID: v1_국내주식-065
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-index-daily-price
    TR_ID: FHPUP02120000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code
            - fid_input_date_1: Start date (YYYYMMDD format)
            - fid_input_date_2: End date (YYYYMMDD format)

    Returns:
        Dictionary containing daily index price data:
            - Array of daily OHLC data
            - Date-wise index movements

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_index_daily_price(
        ...     client,
        ...     fid_input_iscd='001',
        ...     fid_input_date_1='20240101',
        ...     fid_input_date_2='20240131'
        ... )
        >>> for day in result['output']:
        ...     print(f"{day['bas_dt']}: {day['idx_clpr']}")
    """
    api_id = "v1_국내주식-065"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-index-daily-price"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
        "fid_input_date_1": kwargs.get("fid_input_date_1"),
        "fid_input_date_2": kwargs.get("fid_input_date_2"),
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


def get_inquire_index_category_price(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve industry index prices by category (Real trading only).

    API ID: v1_국내주식-066
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-index-category-price
    TR_ID: FHPUP02140000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code
            - fid_cond_mrkt_div_code: Market division code

    Returns:
        Dictionary containing category-wise index prices:
            - All industry sector indices
            - Current prices and changes

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_index_category_price(client)
        >>> if result['rt_cd'] == '0':
        ...     for sector in result['output']:
        ...         print(f"{sector['idx_nm']}: {sector['idx_prpr']}")
    """
    api_id = "v1_국내주식-066"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-index-category-price"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
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


def get_chk_holiday(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic market holiday information (Real trading only).

    API ID: 국내주식-040
    Endpoint: /uapi/domestic-stock/v1/quotations/chk-holiday
    TR_ID: CTCA0903R (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - bas_dt: Base date (YYYYMMDD format) to check holiday

    Returns:
        Dictionary containing holiday information:
            - Whether the specified date is a holiday
            - Holiday name if applicable
            - Next business day

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_chk_holiday(client, bas_dt='20240101')
        >>> if result['rt_cd'] == '0':
        ...     print(f"Holiday: {result['output']['dev_yn']}")
    """
    api_id = "국내주식-040"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/chk-holiday"

    params = {
        "bas_dt": kwargs.get("bas_dt"),
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


def get_inquire_index_tickprice(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve industry index prices by second (tick) (Real trading only).

    API ID: 국내주식-064
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-index-tickprice
    TR_ID: FHPUP02110100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code

    Returns:
        Dictionary containing tick-by-tick index data:
            - Second-level index price movements
            - Real-time index changes

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_index_tickprice(client, fid_input_iscd='001')
        >>> for tick in result['output']:
        ...     print(f"{tick['idx_prpr']} at {tick['cntg_hour']}")
    """
    api_id = "국내주식-064"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-index-tickprice"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
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


def get_inquire_index_timeprice(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve industry index prices by minute (Real trading only).

    API ID: 국내주식-119
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-index-timeprice
    TR_ID: FHPUP02110200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code
            - fid_period_div_code: Time division code

    Returns:
        Dictionary containing minute-level index data:
            - Array of data for each minute
            - Index price per minute

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_inquire_index_timeprice(client, fid_input_iscd='001')
        >>> for minute in result['output']:
        ...     print(f"{minute['idx_prpr']} at {minute['cntg_hour']}")
    """
    api_id = "국내주식-119"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-index-timeprice"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
        "fid_period_div_code": kwargs.get("fid_period_div_code", "1"),
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


def get_exp_index_trend(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve expected settlement index trend (Real trading only).

    API ID: 국내주식-121
    Endpoint: /uapi/domestic-stock/v1/quotations/exp-index-trend
    TR_ID: FHPST01840000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Index code

    Returns:
        Dictionary containing expected settlement index trend:
            - Expected closing index prices
            - Trend data over time

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_exp_index_trend(client, fid_input_iscd='001')
        >>> if result['rt_cd'] == '0':
        ...     print(f"Expected index: {result['output']}")
    """
    api_id = "국내주식-121"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/exp-index-trend"

    params = {
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
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


def get_exp_total_index(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve expected settlement total indices (Real trading only).

    API ID: 국내주식-122
    Endpoint: /uapi/domestic-stock/v1/quotations/exp-total-index
    TR_ID: FHKUP11750000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters

    Returns:
        Dictionary containing expected settlement data for all indices:
            - Expected closing prices for major indices
            - KOSPI, KOSDAQ, and sector indices

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_exp_total_index(client)
        >>> if result['rt_cd'] == '0':
        ...     for index in result['output']:
        ...         print(f"{index['idx_nm']}: {index['exp_prpr']}")
    """
    api_id = "국내주식-122"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/exp-total-index"

    params = {**kwargs}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_news_title(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve market news and disclosure titles (Real trading only).

    API ID: 국내주식-141
    Endpoint: /uapi/domestic-stock/v1/quotations/news-title
    TR_ID: FHKST01011800 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters such as:
            - fid_cond_mrkt_div_code: Market division code
            - fid_input_iscd: Issue code (optional, for stock-specific news)

    Returns:
        Dictionary containing news titles:
            - News headlines
            - Publication time
            - News source

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_news_title(client)
        >>> if result['rt_cd'] == '0':
        ...     for news in result['output']:
        ...         print(f"{news['news_ttl']} - {news['news_dt']}")
    """
    api_id = "국내주식-141"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/news-title"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": kwargs.get("fid_input_iscd"),
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


def get_comp_interest(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve comprehensive interest rates (domestic bonds/rates) (Real trading only).

    API ID: 국내주식-155
    Endpoint: /uapi/domestic-stock/v1/quotations/comp-interest
    TR_ID: FHPST07020000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters

    Returns:
        Dictionary containing comprehensive interest rate data:
            - Government bond yields
            - CD rates
            - Treasury bond rates
            - Key policy rates

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_comp_interest(client)
        >>> if result['rt_cd'] == '0':
        ...     print(f"Interest rates: {result['output']}")
    """
    api_id = "국내주식-155"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/comp-interest"

    params = {**kwargs}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_market_time(
    client: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic futures business day information (Real trading only).

    API ID: 국내주식-160
    Endpoint: /uapi/domestic-stock/v1/quotations/market-time
    TR_ID: HHMCM000002C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        **kwargs: Additional parameters

    Returns:
        Dictionary containing market business day information:
            - Current business day
            - Market open/close times
            - Trading calendar information

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_market_time(client)
        >>> if result['rt_cd'] == '0':
        ...     print(f"Business day: {result['output']}")
    """
    api_id = "국내주식-160"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_DOMESTIC_STOCK_BASE}/market-time"

    params = {**kwargs}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )
