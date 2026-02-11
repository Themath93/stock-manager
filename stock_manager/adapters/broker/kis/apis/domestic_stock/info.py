"""
Domestic Stock Info API Functions

This module provides functions for interacting with KIS OpenAPI
domestic stock info endpoints.

Total APIs: 26

TR_ID Reference:
- All APIs in this module are REAL TRADING ONLY (paper trading not supported)
"""

from typing import Any, Dict

# API Endpoints
_BASE_URL = "https://api.koreainvestment.com"
_DOMESTIC_STOCK_BASE = "/uapi/domestic-stock/v1/quotations"
_FINANCE_BASE = "/uapi/domestic-stock/v1/finance"
_KSDINFO_BASE = "/uapi/domestic-stock/v1/ksdinfo"

# TR_ID Constants (Real Trading Only - Paper Trading Not Supported)
TR_IDS = {
    # Product/Stock Info APIs
    "v1_국내주식-029": "CTPF1604R",  # Search info
    "v1_국내주식-067": "CTPF1002R",  # Search stock info

    # Financial Statement APIs
    "v1_국내주식-078": "FHKST66430100",  # Balance sheet
    "v1_국내주식-079": "FHKST66430200",  # Income statement
    "v1_국내주식-080": "FHKST66430300",  # Financial ratio
    "v1_국내주식-081": "FHKST66430400",  # Profit ratio
    "v1_국내주식-082": "FHKST66430500",  # Other major ratios
    "v1_국내주식-083": "FHKST66430600",  # Stability ratio
    "v1_국내주식-085": "FHKST66430800",  # Growth ratio

    # Credit & Lending APIs
    "국내주식-111": "FHPST04770000",  # Credit by company
    "국내주식-195": "CTSC2702R",      # Lendable by company

    # KSD Info APIs (Corporate Actions)
    "국내주식-143": "HHKDB669100C0",  # Paid-in capital
    "국내주식-144": "HHKDB669101C0",  # Bonus issue
    "국내주식-145": "HHKDB669102C0",  # Dividend
    "국내주식-146": "HHKDB669103C0",  # Purchase request
    "국내주식-147": "HHKDB669104C0",  # Merger/split
    "국내주식-148": "HHKDB669105C0",  # Reverse split
    "국내주식-149": "HHKDB669106C0",  # Capital decrease
    "국내주식-150": "HHKDB669107C0",  # Listing info
    "국내주식-151": "HHKDB669108C0",  # Public offering
    "국내주식-152": "HHKDB669109C0",  # Forfeit
    "국내주식-153": "HHKDB669110C0",  # Mandatory deposit
    "국내주식-154": "HHKDB669111C0",  # Shareholders meeting

    # Investment Opinion APIs
    "국내주식-187": "HHKST668300C0",  # Estimate performance
    "국내주식-188": "FHKST663300C0",  # Investment opinion
    "국내주식-189": "FHKST663400C0",  # Investment opinion by securities
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-029')
        is_paper_trading: Whether to use paper trading TR_ID

    Returns:
        The TR_ID string for the specified environment

    Raises:
        ValueError: If the API_ID is not found or paper trading is not supported
    """
    if api_id not in TR_IDS:
        raise ValueError(f"Unknown API_ID: {api_id}")

    if is_paper_trading:
        raise ValueError(f"Paper trading is not supported for {api_id}")

    return TR_IDS[api_id]


def get_search_info(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve product basic information (search info).

    API ID: v1_국내주식-029
    Endpoint: /uapi/domestic-stock/v1/quotations/search-info
    TR_ID: CTPF1604R (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing product basic information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_search_info(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Product info: {response['output']}")
    """
    api_id = "v1_국내주식-029"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/search-info"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_search_stock_info(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve stock basic information.

    API ID: v1_국내주식-067
    Endpoint: /uapi/domestic-stock/v1/quotations/search-stock-info
    TR_ID: CTPF1002R (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing stock basic information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_search_stock_info(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Stock info: {response['output']}")
    """
    api_id = "v1_국내주식-067"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/search-stock-info"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_balance_sheet(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock balance sheet.

    API ID: v1_국내주식-078
    Endpoint: /uapi/domestic-stock/v1/finance/balance-sheet
    TR_ID: FHKST66430100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing balance sheet data including:
            - Assets
            - Liabilities
            - Equity

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_balance_sheet(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Balance sheet: {response['output']}")
    """
    api_id = "v1_국내주식-078"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/balance-sheet"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_income_statement(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock income statement.

    API ID: v1_국내주식-079
    Endpoint: /uapi/domestic-stock/v1/finance/income-statement
    TR_ID: FHKST66430200 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing income statement data including:
            - Revenue
            - Operating income
            - Net income

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_income_statement(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Income statement: {response['output']}")
    """
    api_id = "v1_국내주식-079"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/income-statement"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_financial_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock financial ratios.

    API ID: v1_국내주식-080
    Endpoint: /uapi/domestic-stock/v1/finance/financial-ratio
    TR_ID: FHKST66430300 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing financial ratio data including:
            - Liquidity ratios
            - Leverage ratios
            - Efficiency ratios

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_financial_ratio(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Financial ratios: {response['output']}")
    """
    api_id = "v1_국내주식-080"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/financial-ratio"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_profit_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock profitability ratios.

    API ID: v1_국내주식-081
    Endpoint: /uapi/domestic-stock/v1/finance/profit-ratio
    TR_ID: FHKST66430400 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing profitability ratios including:
            - ROE (Return on Equity)
            - ROA (Return on Assets)
            - Profit margins

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_profit_ratio(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Profitability ratios: {response['output']}")
    """
    api_id = "v1_국내주식-081"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/profit-ratio"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_other_major_ratios(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve other major financial ratios.

    API ID: v1_국내주식-082
    Endpoint: /uapi/domestic-stock/v1/finance/other-major-ratios
    TR_ID: FHKST66430500 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing other major financial ratios

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_other_major_ratios(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Other ratios: {response['output']}")
    """
    api_id = "v1_국내주식-082"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/other-major-ratios"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_stability_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock stability ratios.

    API ID: v1_국내주식-083
    Endpoint: /uapi/domestic-stock/v1/finance/stability-ratio
    TR_ID: FHKST66430600 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing stability ratios including:
            - Debt-to-equity ratio
            - Current ratio
            - Quick ratio

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_stability_ratio(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Stability ratios: {response['output']}")
    """
    api_id = "v1_국내주식-083"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/stability-ratio"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_growth_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock growth ratios.

    API ID: v1_국내주식-085
    Endpoint: /uapi/domestic-stock/v1/finance/growth-ratio
    TR_ID: FHKST66430800 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing growth ratios including:
            - Revenue growth
            - Income growth
            - Asset growth

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_growth_ratio(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Growth ratios: {response['output']}")
    """
    api_id = "v1_국내주식-085"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_FINANCE_BASE}/growth-ratio"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_credit_by_company(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve credit trading available stocks by company.

    API ID: 국내주식-111
    Endpoint: /uapi/domestic-stock/v1/quotations/credit-by-company
    TR_ID: FHPST04770000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing credit trading available stocks

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_credit_by_company(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Credit stocks: {response['output']}")
    """
    api_id = "국내주식-111"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/credit-by-company"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_paidin_capin(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - paid-in capital schedule.

    API ID: 국내주식-143
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/paidin-capin
    TR_ID: HHKDB669100C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing paid-in capital schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_paidin_capin(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Paid-in capital schedule: {response['output']}")
    """
    api_id = "국내주식-143"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/paidin-capin"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_bonus_issue(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - bonus issue schedule.

    API ID: 국내주식-144
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/bonus-issue
    TR_ID: HHKDB669101C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing bonus issue schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_bonus_issue(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Bonus issue schedule: {response['output']}")
    """
    api_id = "국내주식-144"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/bonus-issue"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_dividend(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - dividend schedule.

    API ID: 국내주식-145
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/dividend
    TR_ID: HHKDB669102C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing dividend schedule information including:
            - Dividend amount
            - Dividend yield
            - Ex-dividend date
            - Payment date

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_dividend(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Dividend schedule: {response['output']}")
    """
    api_id = "국내주식-145"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/dividend"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_purreq(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - stock purchase request schedule.

    API ID: 국내주식-146
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/purreq
    TR_ID: HHKDB669103C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing stock purchase request schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_purreq(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Purchase request schedule: {response['output']}")
    """
    api_id = "국내주식-146"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/purreq"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_merger_split(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - merger/split schedule.

    API ID: 국내주식-147
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/merger-split
    TR_ID: HHKDB669104C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing merger/split schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_merger_split(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Merger/split schedule: {response['output']}")
    """
    api_id = "국내주식-147"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/merger-split"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_rev_split(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - reverse split (par value change) schedule.

    API ID: 국내주식-148
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/rev-split
    TR_ID: HHKDB669105C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing reverse split schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_rev_split(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Reverse split schedule: {response['output']}")
    """
    api_id = "국내주식-148"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/rev-split"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_cap_dcrs(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - capital decrease schedule.

    API ID: 국내주식-149
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/cap-dcrs
    TR_ID: HHKDB669106C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing capital decrease schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_cap_dcrs(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Capital decrease schedule: {response['output']}")
    """
    api_id = "국내주식-149"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/cap-dcrs"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_list_info(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - listing information schedule.

    API ID: 국내주식-150
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/list-info
    TR_ID: HHKDB669107C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing listing information schedule

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_list_info(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Listing info schedule: {response['output']}")
    """
    api_id = "국내주식-150"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/list-info"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_pub_offer(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - public offering schedule.

    API ID: 국내주식-151
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/pub-offer
    TR_ID: HHKDB669108C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing public offering schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_pub_offer(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Public offering schedule: {response['output']}")
    """
    api_id = "국내주식-151"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/pub-offer"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_forfeit(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - forfeit stock schedule.

    API ID: 국내주식-152
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/forfeit
    TR_ID: HHKDB669109C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing forfeit stock schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_forfeit(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Forfeit stock schedule: {response['output']}")
    """
    api_id = "국내주식-152"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/forfeit"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_mand_deposit(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - mandatory deposit schedule.

    API ID: 국내주식-153
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/mand-deposit
    TR_ID: HHKDB669110C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing mandatory deposit schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_mand_deposit(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Mandatory deposit schedule: {response['output']}")
    """
    api_id = "국내주식-153"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/mand-deposit"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_sharehld_meet(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve KSD info - shareholders meeting schedule.

    API ID: 국내주식-154
    Endpoint: /uapi/domestic-stock/v1/ksdinfo/sharehld-meet
    TR_ID: HHKDB669111C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing shareholders meeting schedule information

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_sharehld_meet(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Shareholders meeting schedule: {response['output']}")
    """
    api_id = "국내주식-154"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_KSDINFO_BASE}/sharehld-meet"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_estimate_perform(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock estimated performance.

    API ID: 국내주식-187
    Endpoint: /uapi/domestic-stock/v1/quotations/estimate-perform
    TR_ID: HHKST668300C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing estimated performance data including:
            - Estimated earnings
            - Estimated revenue
            - Analyst recommendations

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_estimate_perform(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Estimated performance: {response['output']}")
    """
    api_id = "국내주식-187"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/estimate-perform"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_invest_opinion(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock investment opinion.

    API ID: 국내주식-188
    Endpoint: /uapi/domestic-stock/v1/quotations/invest-opinion
    TR_ID: FHKST663300C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing investment opinions including:
            - Buy/Hold/Sell recommendations
            - Target prices
            - Analyst consensus

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_invest_opinion(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Investment opinion: {response['output']}")
    """
    api_id = "국내주식-188"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/invest-opinion"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_invest_opbysec(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock investment opinion by securities firm.

    API ID: 국내주식-189
    Endpoint: /uapi/domestic-stock/v1/quotations/invest-opbysec
    TR_ID: FHKST663400C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters such as:
            - fid_input_iscd: Issue code (stock code)

    Returns:
        Dictionary containing investment opinions broken down by securities firm

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_invest_opbysec(client, fid_input_iscd="005930")
        >>> if response['rt_cd'] == '0':
        ...     print(f"Opinion by securities: {response['output']}")
    """
    api_id = "국내주식-189"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/invest-opbysec"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )


def get_lendable_by_company(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve securities lending available stocks by company.

    API ID: 국내주식-195
    Endpoint: /uapi/domestic-stock/v1/quotations/lendable-by-company
    TR_ID: CTSC2702R (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        Dictionary containing securities lending available stocks

    Raises:
        ValueError: If paper trading is attempted (not supported)

    Examples:
        >>> response = get_lendable_by_company(client)
        >>> if response['rt_cd'] == '0':
        ...     print(f"Lendable stocks: {response['output']}")
    """
    api_id = "국내주식-195"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_BASE_URL}{_DOMESTIC_STOCK_BASE}/lendable-by-company"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="GET",
        path=path,
        params=kwargs,
        headers=headers,
    )
