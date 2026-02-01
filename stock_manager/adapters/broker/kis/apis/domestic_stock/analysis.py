"""
Domestic Stock Analysis APIs for KIS (Korea Investment Securities) OpenAPI.

This module provides functions for domestic stock market analysis including:
- Program trading trends
- Investor trading patterns
- Short selling data
- Credit balance trends
- Market funds analysis
- Foreign/institutional trading data

Total APIs: 29
"""

from typing import Any, Dict

# API Endpoints
_BASE_URL = "https://api.koreainvestment.com"
_DOMESTIC_STOCK_BASE = "/uapi/domestic-stock/v1/quotations"
_DOMESTIC_STOCK_RANKING = "/uapi/domestic-stock/v1/ranking"

# TR_ID Constants
TR_IDS = {
    # v1 APIs
    "v1_국내주식-044": {"real": "FHPPG04650101", "paper": None},  # Program trade by stock (execution)
    "v1_국내주식-046": {"real": "HHPTJ04160200", "paper": None},  # Investor trend estimate
    "v1_국내주식-056": {"real": "FHKST03010800", "paper": None},  # Daily trade volume
    "v1_국내주식-074": {"real": "FHPTJ04030000", "paper": None},  # Investor time by market

    # Standard APIs
    "국내주식-037": {"real": "FHPTJ04400000", "paper": None},  # Foreign institution total
    "국내주식-038": {"real": "HHKST03900300", "paper": None},  # Psearch title
    "국내주식-039": {"real": "HHKST03900400", "paper": None},  # Psearch result
    "국내주식-075": {"real": "FHPTJ04040000", "paper": None},  # Investor daily by market
    "국내주식-110": {"real": "FHPST04760000", "paper": None},  # Daily credit balance
    "국내주식-113": {"real": "FHPPG04650201", "paper": None},  # Program trade by stock daily
    "국내주식-114": {"real": "FHPPG04600101", "paper": None},  # Comp program trade today
    "국내주식-115": {"real": "FHPPG04600001", "paper": None},  # Comp program trade daily
    "국내주식-116": {"real": "HHPPG046600C1", "paper": None},  # Investor program trade today
    "국내주식-118": {"real": "FHPST01810000", "paper": None},  # Exp price trend
    "국내주식-134": {"real": "FHPST04830000", "paper": None},  # Daily short sale
    "국내주식-135": {"real": "HHPST074500C0", "paper": None},  # Daily loan transactions
    "국내주식-140": {"real": "FHKST11860000", "paper": None},  # Overtime exp trans fluct
    "국내주식-161": {"real": "FHKST644100C0", "paper": None},  # Foreign member trade estimate
    "국내주식-163": {"real": "FHPST04320000", "paper": None},  # Foreign member trade trend
    "국내주식-164": {"real": "FHKST644400C0", "paper": None},  # Foreign member purchase trend
    "국내주식-190": {"real": "FHKST130000C0", "paper": None},  # Capture uplow price
    "국내주식-192": {"real": "FHKST111900C0", "paper": None},  # Trading proportion by amount
    "국내주식-193": {"real": "FHKST649100C0", "paper": None},  # Market funds
    "국내주식-196": {"real": "FHPST01130000", "paper": None},  # Price band trading ratio
    "국내주식-197": {"real": "FHPST04540000", "paper": None},  # Inquire member daily
    "국내주식-203": {"real": "HHKCM113004C6", "paper": None},  # Intstock stocklist by group
    "국내주식-204": {"real": "HHKCM113004C7", "paper": None},  # Intstock grouplist
    "국내주식-205": {"real": "FHKST11300006", "paper": None},  # Intstock multprice
    "종목별 투자자매매동향(일별)": {"real": "FHPTJ04160001", "paper": None},  # Investor trade by stock daily
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-044')
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


def get_program_trade_by_stock(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve program trading trends by stock (execution).

    API ID: v1_국내주식-044
    Endpoint: /uapi/domestic-stock/v1/quotations/program-trade-by-stock
    TR_ID: FHPPG04650101 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing program trading execution data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_program_trade_by_stock(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "v1_국내주식-044"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/program-trade-by-stock"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_investor_trend_estimate(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve foreign investor and institutional estimated price aggregation.

    API ID: v1_국내주식-046
    Endpoint: /uapi/domestic-stock/v1/quotations/investor-trend-estimate
    TR_ID: HHPTJ04160200 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing investor trend estimate data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_investor_trend_estimate(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "v1_국내주식-046"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/investor-trend-estimate"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_inquire_daily_trade_volume(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily buy/sell execution volume by stock.

    API ID: v1_국내주식-056
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume
    TR_ID: FHKST03010800 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily trade volume data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_inquire_daily_trade_volume(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "v1_국내주식-056"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-daily-trade-volume"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_inquire_investor_time_by_market(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve investor trading trends by market (quotes/time-series).

    API ID: v1_국내주식-074
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market
    TR_ID: FHPTJ04030000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing time-series investor trading trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_inquire_investor_time_by_market(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "v1_국내주식-074"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-investor-time-by-market"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_foreign_institution_total(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic institution and foreigner trading price aggregation.

    API ID: 국내주식-037
    Endpoint: /uapi/domestic-stock/v1/quotations/foreign-institution-total
    TR_ID: FHPTJ04400000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing institution/foreigner trading data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_foreign_institution_total(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-037"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/foreign-institution-total"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_psearch_title(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve stock condition search title list.

    API ID: 국내주식-038
    Endpoint: /uapi/domestic-stock/v1/quotations/psearch-title
    TR_ID: HHKST03900300 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing condition search titles

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_psearch_title(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-038"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/psearch-title"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_psearch_result(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve stock condition search result.

    API ID: 국내주식-039
    Endpoint: /uapi/domestic-stock/v1/quotations/psearch-result
    TR_ID: HHKST03900400 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing condition search results

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_psearch_result(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-039"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/psearch-result"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_inquire_investor_daily_by_market(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve investor trading trends by market (daily).

    API ID: 국내주식-075
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market
    TR_ID: FHPTJ04040000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily investor trading trends by market

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_inquire_investor_daily_by_market(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-075"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-investor-daily-by-market"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_daily_credit_balance(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily credit balance trends.

    API ID: 국내주식-110
    Endpoint: /uapi/domestic-stock/v1/quotations/daily-credit-balance
    TR_ID: FHPST04760000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily credit balance trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_daily_credit_balance(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-110"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/daily-credit-balance"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_program_trade_by_stock_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve program trading trends by stock (daily).

    API ID: 국내주식-113
    Endpoint: /uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily
    TR_ID: FHPPG04650201 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily program trading trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_program_trade_by_stock_daily(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-113"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/program-trade-by-stock-daily"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_comp_program_trade_today(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve comprehensive program trading status (time/today).

    API ID: 국내주식-114
    Endpoint: /uapi/domestic-stock/v1/quotations/comp-program-trade-today
    TR_ID: FHPPG04600101 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing comprehensive program trading status

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_comp_program_trade_today(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-114"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/comp-program-trade-today"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_comp_program_trade_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve comprehensive program trading status (daily).

    API ID: 국내주식-115
    Endpoint: /uapi/domestic-stock/v1/quotations/comp-program-trade-daily
    TR_ID: FHPPG04600001 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily comprehensive program trading status

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_comp_program_trade_daily(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-115"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/comp-program-trade-daily"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_investor_program_trade_today(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve program trading investor trading trends (today).

    API ID: 국내주식-116
    Endpoint: /uapi/domestic-stock/v1/quotations/investor-program-trade-today
    TR_ID: HHPPG046600C1 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing investor program trading trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_investor_program_trade_today(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-116"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/investor-program-trade-today"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_exp_price_trend(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve expected conclusion price trend.

    API ID: 국내주식-118
    Endpoint: /uapi/domestic-stock/v1/quotations/exp-price-trend
    TR_ID: FHPST01810000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing expected price trend data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_exp_price_trend(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-118"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/exp-price-trend"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_daily_short_sale(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily short selling trends.

    API ID: 국내주식-134
    Endpoint: /uapi/domestic-stock/v1/quotations/daily-short-sale
    TR_ID: FHPST04830000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily short selling data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_daily_short_sale(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-134"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/daily-short-sale"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_daily_loan_transactions(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve daily loan transaction trends by stock.

    API ID: 국내주식-135
    Endpoint: /uapi/domestic-stock/v1/quotations/daily-loan-trans
    TR_ID: HHPST074500C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing daily loan transaction data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_daily_loan_transactions(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-135"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/daily-loan-trans"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_overtime_exp_trans_fluct(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve overtime expected conclusion transaction fluctuation rate.

    API ID: 국내주식-140
    Endpoint: /uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct
    TR_ID: FHKST11860000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing overtime fluctuation data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_overtime_exp_trans_fluct(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-140"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_RANKING}/overtime-exp-trans-fluct"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_foreign_member_trade_estimate(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve foreign member trading volume aggregation.

    API ID: 국내주식-161
    Endpoint: /uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate
    TR_ID: FHKST644100C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing foreign member trading estimates

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_foreign_member_trade_estimate(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-161"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/frgnmem-trade-estimate"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_foreign_member_trade_trend(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve member company real-time trading trends (tick).

    API ID: 국내주식-163
    Endpoint: /uapi/domestic-stock/v1/quotations/frgnmem-trade-trend
    TR_ID: FHPST04320000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing real-time trading trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_foreign_member_trade_trend(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-163"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/frgnmem-trade-trend"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_foreign_member_purchase_trend(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve net purchase trend by foreign member by stock.

    API ID: 국내주식-164
    Endpoint: /uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend
    TR_ID: FHKST644400C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing foreign member purchase trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_foreign_member_purchase_trend(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-164"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/frgnmem-pchs-trend"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_capture_uplow_price(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock upper/lower limit price capture.

    API ID: 국내주식-190
    Endpoint: /uapi/domestic-stock/v1/quotations/capture-uplowprice
    TR_ID: FHKST130000C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing upper/lower limit price data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_capture_uplow_price(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-190"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/capture-uplowprice"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_tradprt_byamt(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock trading proportion by amount.

    API ID: 국내주식-192
    Endpoint: /uapi/domestic-stock/v1/quotations/tradprt-byamt
    TR_ID: FHKST111900C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing trading proportion data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_tradprt_byamt(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-192"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/tradprt-byamt"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_mktfunds(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic market funds comprehensive data.

    API ID: 국내주식-193
    Endpoint: /uapi/domestic-stock/v1/quotations/mktfunds
    TR_ID: FHKST649100C0 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing market funds data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_mktfunds(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-193"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/mktfunds"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_pbar_tratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock price band trading ratio.

    API ID: 국내주식-196
    Endpoint: /uapi/domestic-stock/v1/quotations/pbar-tratio
    TR_ID: FHPST01130000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing price band trading ratio data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_pbar_tratio(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-196"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/pbar-tratio"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_inquire_member_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve stock price member company trading trends (daily).

    API ID: 국내주식-197
    Endpoint: /uapi/domestic-stock/v1/quotations/inquire-member-daily
    TR_ID: FHPST04540000 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing member trading trends

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_inquire_member_daily(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-197"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/inquire-member-daily"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_investor_trade_by_stock_daily(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve investor trading trends by stock (daily).

    API ID: 종목별 투자자매매동향(일별)
    Endpoint: /uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily
    TR_ID: FHPTJ04160001 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing investor trading trends by stock

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_investor_trade_by_stock_daily(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "종목별 투자자매매동향(일별)"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/investor-trade-by-stock-daily"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_intstock_stocklist_by_group(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve interest stock group-wise stock list.

    API ID: 국내주식-203
    Endpoint: /uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group
    TR_ID: HHKCM113004C6 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing interest stock list by group

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_intstock_stocklist_by_group(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-203"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/intstock-stocklist-by-group"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_intstock_grouplist(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve interest stock group list.

    API ID: 국내주식-204
    Endpoint: /uapi/domestic-stock/v1/quotations/intstock-grouplist
    TR_ID: HHKCM113004C7 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing interest stock group list

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_intstock_grouplist(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-204"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/intstock-grouplist"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_intstock_multprice(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve interest stock multi-stock price inquiry.

    API ID: 국내주식-205
    Endpoint: /uapi/domestic-stock/v1/quotations/intstock-multprice
    TR_ID: FHKST11300006 (Real only - Paper trading not supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing multi-stock price data

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> response = get_intstock_multprice(client)
        >>> if response['rt_cd'] == '0':
        ...     print("Success:", response.get('output'))
    """
    api_id = "국내주식-205"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_DOMESTIC_STOCK_BASE}/intstock-multprice"

    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )
