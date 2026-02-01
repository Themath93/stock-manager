"""
Domestic Stock ELW (ELW: Exchange Traded Warrant) APIs for KIS (Korea Investment Securities) OpenAPI.

This module provides functions to query ELW-related information including current prices,
rankings, trends, and various indicators for ELW securities.

ELW (Exchange Listed Warrant) is a type of warrant that is traded on the stock exchange.
It gives the holder the right to buy or sell the underlying asset at a specified price
within a specified time period.

TR_ID Reference:
- Real Trading: Production environment TR_IDs
- Paper Trading: Simulation environment TR_IDs (limited support)
"""

from typing import Any, Dict

# API Endpoints
_BASE_URL = "https://api.koreainvestment.com"
_DOMESTIC_STOCK_BASE = "/uapi/domestic-stock/v1/quotations"
_ELW_BASE = "/uapi/elw/v1"

# TR_ID Constants
TR_IDS = {
    # Both real and paper trading supported
    "v1_국내주식-014": {"real": "FHKEW15010000", "paper": "FHKEW15010000"},  # ELW current price

    # Real trading only (paper trading not supported)
    "국내주식-166": {"real": "FHKEW15100000", "paper": None},     # ELW condition search
    "국내주식-167": {"real": "FHPEW02770000", "paper": None},     # ELW up/down rate ranking
    "국내주식-168": {"real": "FHPEW02780000", "paper": None},     # ELW volume ranking
    "국내주식-169": {"real": "FHPEW02790000", "paper": None},     # ELW indicator ranking
    "국내주식-170": {"real": "FHPEW02850000", "paper": None},     # ELW sensitivity ranking
    "국내주식-171": {"real": "FHPEW02870000", "paper": None},     # ELW quick change stocks
    "국내주식-172": {"real": "FHPEW02740100", "paper": None},     # ELW indicator trend (conclusion)
    "국내주식-173": {"real": "FHPEW02740200", "paper": None},     # ELW indicator trend (daily)
    "국내주식-174": {"real": "FHPEW02740300", "paper": None},     # ELW indicator trend (minute)
    "국내주식-175": {"real": "FHPEW02830100", "paper": None},     # ELW sensitivity trend (conclusion)
    "국내주식-176": {"real": "FHPEW02830200", "paper": None},     # ELW sensitivity trend (daily)
    "국내주식-177": {"real": "FHPEW02840100", "paper": None},     # ELW volatility trend (conclusion)
    "국내주식-178": {"real": "FHPEW02840200", "paper": None},     # ELW volatility trend (daily)
    "국내주식-179": {"real": "FHPEW02840300", "paper": None},     # ELW volatility trend (minute)
    "국내주식-180": {"real": "FHPEW02840400", "paper": None},     # ELW volatility trend (tick)
    "국내주식-181": {"real": "FHKEW154800C0", "paper": None},     # ELW newly listed stocks
    "국내주식-182": {"real": "FHPEW03760000", "paper": None},     # ELW LP trading trend
    "국내주식-183": {"real": "FHKEW151701C0", "paper": None},     # ELW compare stocks
    "국내주식-184": {"real": "FHKEW154700C0", "paper": None},     # ELW expiration stocks
    "국내주식-185": {"real": "FHKEW154100C0", "paper": None},     # ELW underlying asset list
    "국내주식-186": {"real": "FHKEW154101C0", "paper": None},     # ELW underlying asset price
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-014')
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


def inquire_elw_price(
    client: Any,
    elw_code: str,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve current ELW (Exchange Listed Warrant) price information.

    API ID: v1_국내주식-014
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-elw-price
    TR_ID: FHKEW15010000 (Real), FHKEW15010000 (Paper)

    Args:
        client: KISRestClient instance for making API requests
        elw_code: 6-digit ELW code
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW current price data:
            - Current market price
            - Price changes
            - Trading volume

    Raises:
        ValueError: If invalid parameters are provided
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = inquire_elw_price(client, '001234')
        >>> if result['rt_cd'] == '0':
        ...     print(f"ELW Price: {result['output']['stck_prpr']}")
    """
    api_id = "v1_국내주식-014"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-elw-price"

    params = {
        "fid_cond_mrkt_div_code": kwargs.get("fid_cond_mrkt_div_code", "J"),
        "fid_input_iscd": elw_code,
    }

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def cond_search(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Search ELW stocks by conditions (filters).

    API ID: 국내주식-166
    Endpoint: /uapi/elw/v1/quotations/cond-search
    TR_ID: FHKEW15100000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters for search conditions

    Returns:
        Dictionary containing ELW search results matching specified conditions

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = cond_search(client)
        >>> for elw in result.get('output', []):
        ...     print(f"ELW: {elw['name']} ({elw['code']})")
    """
    api_id = "국내주식-166"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/cond-search"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def updown_rate(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW ranking by up/down rate (price change percentage).

    API ID: 국내주식-167
    Endpoint: /uapi/elw/v1/ranking/updown-rate
    TR_ID: FHPEW02770000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW ranking by up/down rate:
            - Rank number
            - ELW code
            - Up/down rate percentage

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = updown_rate(client)
        >>> for elw in result.get('output', []):
        ...     print(f"Rank {elw['rank']}: {elw['name']} ({elw['rate']}%)")
    """
    api_id = "국내주식-167"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/ranking/updown-rate"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def volume_rank(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW ranking by trading volume.

    API ID: 국내주식-168
    Endpoint: /uapi/elw/v1/ranking/volume-rank
    TR_ID: FHPEW02780000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW ranking by trading volume:
            - Rank number
            - ELW code
            - Trading volume

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = volume_rank(client)
        >>> for elw in result.get('output', []):
        ...     print(f"Rank {elw['rank']}: {elw['name']} (Vol: {elw['volume']})")
    """
    api_id = "국내주식-168"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/ranking/volume-rank"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def indicator(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW ranking by various indicators.

    API ID: 국내주식-169
    Endpoint: /uapi/elw/v1/ranking/indicator
    TR_ID: FHPEW02790000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW ranking by indicators:
            - Rank number
            - ELW code
            - Indicator values (delta, gamma, theta, vega, etc.)

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = indicator(client)
        >>> for elw in result.get('output', []):
        ...     print(f"Rank {elw['rank']}: {elw['name']} (Delta: {elw['delta']})")
    """
    api_id = "국내주식-169"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/ranking/indicator"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def sensitivity(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW ranking by sensitivity (price sensitivity to underlying asset).

    API ID: 국내주식-170
    Endpoint: /uapi/elw/v1/ranking/sensitivity
    TR_ID: FHPEW02850000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW ranking by sensitivity:
            - Rank number
            - ELW code
            - Sensitivity values

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = sensitivity(client)
        >>> for elw in result.get('output', []):
        ...     print(f"Rank {elw['rank']}: {elw['name']} (Sensitivity: {elw['sensitivity']})")
    """
    api_id = "국내주식-170"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/ranking/sensitivity"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def quick_change(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW stocks with rapid price changes (quick change stocks).

    API ID: 국내주식-171
    Endpoint: /uapi/elw/v1/ranking/quick-change
    TR_ID: FHPEW02870000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW stocks with rapid price changes:
            - ELW code
            - Price change rate
            - Current price

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = quick_change(client)
        >>> for elw in result.get('output', []):
        ...     print(f"{elw['name']}: {elw['rate']}% change")
    """
    api_id = "국내주식-171"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/ranking/quick-change"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def indicator_trend_ccnl(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW investment indicator trend (conclusion/tick data).

    API ID: 국내주식-172
    Endpoint: /uapi/elw/v1/quotations/indicator-trend-ccnl
    TR_ID: FHPEW02740100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW indicator trend by conclusion:
            - Time series data
            - Indicator values over time

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = indicator_trend_ccnl(client)
        >>> for data in result.get('output', []):
        ...     print(f"Time: {data['time']}, Delta: {data['delta']}")
    """
    api_id = "국내주식-172"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/indicator-trend-ccnl"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def indicator_trend_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW investment indicator trend (daily data).

    API ID: 국내주식-173
    Endpoint: /uapi/elw/v1/quotations/indicator-trend-daily
    TR_ID: FHPEW02740200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW indicator trend by day:
            - Daily indicator values
            - Historical trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = indicator_trend_daily(client)
        >>> for data in result.get('output', []):
        ...     print(f"Date: {data['date']}, Delta: {data['delta']}")
    """
    api_id = "국내주식-173"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/indicator-trend-daily"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def indicator_trend_minute(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW investment indicator trend (minute data).

    API ID: 국내주식-174
    Endpoint: /uapi/elw/v1/quotations/indicator-trend-minute
    TR_ID: FHPEW02740300 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW indicator trend by minute:
            - Minute-by-minute indicator values
            - Intraday trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = indicator_trend_minute(client)
        >>> for data in result.get('output', []):
        ...     print(f"Time: {data['time']}, Delta: {data['delta']}")
    """
    api_id = "국내주식-174"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/indicator-trend-minute"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def sensitivity_trend_ccnl(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW sensitivity trend (conclusion/tick data).

    API ID: 국내주식-175
    Endpoint: /uapi/elw/v1/quotations/sensitivity-trend-ccnl
    TR_ID: FHPEW02830100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW sensitivity trend by conclusion:
            - Time series sensitivity data
            - Delta, gamma trends

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = sensitivity_trend_ccnl(client)
        >>> for data in result.get('output', []):
        ...     print(f"Time: {data['time']}, Delta: {data['delta']}")
    """
    api_id = "국내주식-175"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/sensitivity-trend-ccnl"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def sensitivity_trend_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW sensitivity trend (daily data).

    API ID: 국내주식-176
    Endpoint: /uapi/elw/v1/quotations/sensitivity-trend-daily
    TR_ID: FHPEW02830200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW sensitivity trend by day:
            - Daily sensitivity values
            - Historical trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = sensitivity_trend_daily(client)
        >>> for data in result.get('output', []):
        ...     print(f"Date: {data['date']}, Delta: {data['delta']}")
    """
    api_id = "국내주식-176"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/sensitivity-trend-daily"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def volatility_trend_ccnl(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW volatility trend (conclusion/tick data).

    API ID: 국내주식-177
    Endpoint: /uapi/elw/v1/quotations/volatility-trend-ccnl
    TR_ID: FHPEW02840100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW volatility trend by conclusion:
            - Time series volatility data
            - Implied volatility values

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = volatility_trend_ccnl(client)
        >>> for data in result.get('output', []):
        ...     print(f"Time: {data['time']}, IV: {data['iv']}")
    """
    api_id = "국내주식-177"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/volatility-trend-ccnl"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def volatility_trend_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW volatility trend (daily data).

    API ID: 국내주식-178
    Endpoint: /uapi/elw/v1/quotations/volatility-trend-daily
    TR_ID: FHPEW02840200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW volatility trend by day:
            - Daily volatility values
            - Historical trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = volatility_trend_daily(client)
        >>> for data in result.get('output', []):
        ...     print(f"Date: {data['date']}, IV: {data['iv']}")
    """
    api_id = "국내주식-178"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/volatility-trend-daily"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def volatility_trend_minute(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW volatility trend (minute data).

    API ID: 국내주식-179
    Endpoint: /uapi/elw/v1/quotations/volatility-trend-minute
    TR_ID: FHPEW02840300 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW volatility trend by minute:
            - Minute-by-minute volatility values
            - Intraday trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = volatility_trend_minute(client)
        >>> for data in result.get('output', []):
        ...     print(f"Time: {data['time']}, IV: {data['iv']}")
    """
    api_id = "국내주식-179"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/volatility-trend-minute"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def volatility_trend_tick(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW volatility trend (tick data).

    API ID: 국내주식-180
    Endpoint: /uapi/elw/v1/quotations/volatility-trend-tick
    TR_ID: FHPEW02840400 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW volatility trend by tick:
            - Tick-by-tick volatility values
            - High-frequency trend data

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = volatility_trend_tick(client)
        >>> for data in result.get('output', []):
        ...     print(f"Tick: {data['tick']}, IV: {data['iv']}")
    """
    api_id = "국내주식-180"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/volatility-trend-tick"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def newly_listed(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve newly listed ELW stocks.

    API ID: 국내주식-181
    Endpoint: /uapi/elw/v1/quotations/newly-listed
    TR_ID: FHKEW154800C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing newly listed ELW stocks:
            - ELW code
            - Listing date
            - Basic information

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = newly_listed(client)
        >>> for elw in result.get('output', []):
        ...     print(f"New ELW: {elw['name']} (Listed: {elw['list_date']})")
    """
    api_id = "국내주식-181"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/newly-listed"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def lp_trade_trend(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW LP (Liquidity Provider) trading trend.

    API ID: 국내주식-182
    Endpoint: /uapi/elw/v1/quotations/lp-trade-trend
    TR_ID: FHPEW03760000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing LP trading trend data:
            - LP trading volume
            - LP trading patterns
            - Market maker activity

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = lp_trade_trend(client)
        >>> for data in result.get('output', []):
        ...     print(f"LP: {data['lp_name']}, Volume: {data['volume']}")
    """
    api_id = "국내주식-182"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/lp-trade-trend"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def compare_stocks(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW comparison target stocks (underlying asset comparison).

    API ID: 국내주식-183
    Endpoint: /uapi/elw/v1/quotations/compare-stocks
    TR_ID: FHKEW151701C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing comparable ELW stocks:
            - Comparison targets
            - Underlying asset information
            - Related ELW securities

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = compare_stocks(client)
        >>> for stock in result.get('output', []):
        ...     print(f"Comparable: {stock['name']} ({stock['code']})")
    """
    api_id = "국내주식-183"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/compare-stocks"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def expiration_stocks(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW stocks approaching maturity or at maturity (expiration).

    API ID: 국내주식-184
    Endpoint: /uapi/elw/v1/quotations/expiration-stocks
    TR_ID: FHKEW154700C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW expiration stocks:
            - ELW code
            - Expiration date
            - Days to expiration

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = expiration_stocks(client)
        >>> for elw in result.get('output', []):
        ...     print(f"Expiring: {elw['name']} (Exp: {elw['exp_date']})")
    """
    api_id = "국내주식-184"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/expiration-stocks"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def udrl_asset_list(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW underlying asset list.

    API ID: 국내주식-185
    Endpoint: /uapi/elw/v1/quotations/udrl-asset-list
    TR_ID: FHKEW154100C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing underlying asset list:
            - Asset code
            - Asset name
            - Available ELW securities

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = udrl_asset_list(client)
        >>> for asset in result.get('output', []):
        ...     print(f"Underlying: {asset['name']} ({asset['code']})")
    """
    api_id = "국내주식-185"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/udrl-asset-list"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def udrl_asset_price(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve ELW stock prices by underlying asset.

    API ID: 국내주식-186
    Endpoint: /uapi/elw/v1/quotations/udrl-asset-price
    TR_ID: FHKEW154101C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading (default: False)
        **kwargs: Additional parameters

    Returns:
        Dictionary containing ELW prices by underlying asset:
            - Underlying asset code
            - Associated ELW prices
            - Price information

    Raises:
        ValueError: If paper trading is attempted
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = udrl_asset_price(client)
        >>> for elw in result.get('output', []):
        ...     print(f"ELW: {elw['name']}, Price: {elw['price']}")
    """
    api_id = "국내주식-186"
    tr_id = _get_tr_id(api_id, is_paper_trading=False)

    path = f"{_ELW_BASE}/quotations/udrl-asset-price"

    params = {**kwargs}
    params = {k: v for k, v in params.items() if v is not None}

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )
