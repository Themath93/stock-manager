"""
Domestic Stock Ranking APIs for KIS (Korea Investment Securities) OpenAPI.

This module provides functions to query domestic stock ranking information
including volume ranks, market cap, fluctuation rates, and various
financial metrics rankings.

TR_ID Reference:
- Real Trading: Production environment TR_IDs
- Paper Trading: Not supported for ranking APIs
"""

from typing import Any, Dict

# API Endpoints
_BASE_URL = "https://api.koreainvestment.com"
_RANKING_BASE = "/uapi/domestic-stock/v1/ranking"
_QUOTATIONS_BASE = "/uapi/domestic-stock/v1/quotations"

# TR_ID Constants
TR_IDS = {
    # Paper trading NOT supported for any ranking APIs
    "v1_국내주식-047": {"real": "FHPST01710000", "paper": None},  # Volume rank
    "v1_국내주식-088": {"real": "FHPST01700000", "paper": None},  # Fluctuation
    "v1_국내주식-090": {"real": "FHPST01730000", "paper": None},  # Profit asset index
    "v1_국내주식-091": {"real": "FHPST01740000", "paper": None},  # Market cap
    "v1_국내주식-092": {"real": "FHPST01750000", "paper": None},  # Finance ratio
    "v1_국내주식-093": {"real": "FHPST01760000", "paper": None},  # After hour balance
    "v1_국내주식-094": {"real": "FHPST01770000", "paper": None},  # Prefer disparate ratio
    "v1_국내주식-095": {"real": "FHPST01780000", "paper": None},  # Disparity
    "v1_국내주식-096": {"real": "FHPST01790000", "paper": None},  # Market value
    "v1_국내주식-101": {"real": "FHPST01680000", "paper": None},  # Volume power
    "v1_국내주식-102": {"real": "FHPST01800000", "paper": None},  # Top interest stock
    "v1_국내주식-103": {"real": "FHPST01820000", "paper": None},  # Expected trans up/down
    "v1_국내주식-104": {"real": "FHPST01860000", "paper": None},  # Traded by company
    "v1_국내주식-105": {"real": "FHPST01870000", "paper": None},  # Near new high/low
    "국내주식-089": {"real": "FHPST01720000", "paper": None},    # Quote balance
    "국내주식-106": {"real": "HHKDB13470100", "paper": None},    # Dividend rate
    "국내주식-107": {"real": "FHKST190900C0", "paper": None},    # Bulk trans num
    "국내주식-109": {"real": "FHKST17010000", "paper": None},    # Credit balance
    "국내주식-133": {"real": "FHPST04820000", "paper": None},    # Short sale
    "국내주식-138": {"real": "FHPST02340000", "paper": None},    # Overtime fluctuation
    "국내주식-139": {"real": "FHPST02350000", "paper": None},    # Overtime volume
    "국내주식-214": {"real": "HHMCM000100C0", "paper": None},    # HTS top view
}


def _get_tr_id(api_id: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        api_id: The API identifier (e.g., 'v1_국내주식-047')
        is_paper_trading: Whether to use paper trading TR_ID

    Returns:
        The TR_ID string for the specified environment

    Raises:
        ValueError: If the API_ID is not found or paper trading is requested but not supported
    """
    if api_id not in TR_IDS:
        raise ValueError(f"Unknown API_ID: {api_id}")

    tr_id_info = TR_IDS[api_id]

    if is_paper_trading:
        if tr_id_info["paper"] is None:
            raise ValueError(f"Paper trading is not supported for {api_id}")
        return tr_id_info["paper"]

    return tr_id_info["real"]


def get_volume_rank(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve trading volume ranking for domestic stocks.

    API ID: v1_국내주식-047
    Endpoint: /uapi/domestic-stock/v1/quotations/volume-rank
    TR_ID: FHPST01710000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing volume ranking data:
            - rt_cd: Return code ('0' for success)
            - msg_cd: Message code
            - msg1: Message description
            - output: Array of ranked stocks by volume

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_volume_rank(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Volume: {stock.get('volume')}")
    """
    api_id = "v1_국내주식-047"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_QUOTATIONS_BASE}/volume-rank"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_fluctuation(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock fluctuation rate ranking.

    API ID: v1_국내주식-088
    Endpoint: /uapi/domestic-stock/v1/ranking/fluctuation
    TR_ID: FHPST01700000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing fluctuation ranking data:
            - Stocks ranked by price change rate
            - Up/down indicators
            - Percentage changes

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_fluctuation(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Change: {stock.get('change_rate')}%")
    """
    api_id = "v1_국내주식-088"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/fluctuation"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_profit_asset_index(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock profit asset index ranking.

    API ID: v1_국내주식-090
    Endpoint: /uapi/domestic-stock/v1/ranking/profit-asset-index
    TR_ID: FHPST01730000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing profit asset index ranking data:
            - Stocks ranked by profitability indicators
            - ROE, ROA metrics
            - Asset efficiency ratios

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_profit_asset_index(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, ROE: {stock.get('roe')}")
    """
    api_id = "v1_국내주식-090"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/profit-asset-index"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_market_cap(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock market capitalization ranking (top stocks).

    API ID: v1_국내주식-091
    Endpoint: /uapi/domestic-stock/v1/ranking/market-cap
    TR_ID: FHPST01740000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing market cap ranking data:
            - Stocks ranked by market capitalization
            - Market cap values
            - Ranking positions

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_market_cap(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Rank: {stock.get('rank')}, Market Cap: {stock.get('market_cap')}")
    """
    api_id = "v1_국내주식-091"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/market-cap"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_finance_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock financial ratio ranking.

    API ID: v1_국내주식-092
    Endpoint: /uapi/domestic-stock/v1/ranking/finance-ratio
    TR_ID: FHPST01750000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing financial ratio ranking data:
            - Stocks ranked by financial ratios
            - Debt-to-equity ratios
            - Liquidity ratios

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_finance_ratio(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, DER: {stock.get('debt_equity_ratio')}")
    """
    api_id = "v1_국내주식-092"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/finance-ratio"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_after_hour_balance(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock after-hours remaining volume ranking.

    API ID: v1_국내주식-093
    Endpoint: /uapi/domestic-stock/v1/ranking/after-hour-balance
    TR_ID: FHPST01760000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing after-hours balance ranking data:
            - Remaining buy/sell orders after market close
            - Order imbalances

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_after_hour_balance(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Balance: {stock.get('balance')}")
    """
    api_id = "v1_국내주식-093"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/after-hour-balance"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_prefer_disparate_ratio(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock preferred stock/disparate ratio ranking.

    API ID: v1_국내주식-094
    Endpoint: /uapi/domestic-stock/v1/ranking/prefer-disparate-ratio
    TR_ID: FHPST01770000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing preferred stock disparate ratio data:
            - Preferred vs common stock price differences
            - Disparity ratios

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_prefer_disparate_ratio(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Disparity: {stock.get('disparity_ratio')}")
    """
    api_id = "v1_국내주식-094"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/prefer-disparate-ratio"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_disparity(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock disparity (price gap) ranking.

    API ID: v1_국내주식-095
    Endpoint: /uapi/domestic-stock/v1/ranking/disparity
    TR_ID: FHPST01780000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing disparity ranking data:
            - Price disparity from moving averages
            - Overbought/oversold indicators

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_disparity(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Disparity: {stock.get('disparity')}")
    """
    api_id = "v1_국내주식-095"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/disparity"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_market_value(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock market value ranking.

    API ID: v1_국내주식-096
    Endpoint: /uapi/domestic-stock/v1/ranking/market-value
    TR_ID: FHPST01790000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing market value ranking data:
            - Stocks ranked by market value indicators
            - Value metrics

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_market_value(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Value: {stock.get('market_value')}")
    """
    api_id = "v1_국내주식-096"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/market-value"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_volume_power(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock trading volume power ranking (conclusion intensity).

    API ID: v1_국내주식-101
    Endpoint: /uapi/domestic-stock/v1/ranking/volume-power
    TR_ID: FHPST01680000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing volume power ranking data:
            - Stocks ranked by trading intensity
            - Buying/selling power ratios

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_volume_power(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Power: {stock.get('volume_power')}")
    """
    api_id = "v1_국내주식-101"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/volume-power"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_top_interest_stock(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stocks most frequently registered in user watchlists.

    API ID: v1_국내주식-102
    Endpoint: /uapi/domestic-stock/v1/ranking/top-interest-stock
    TR_ID: FHPST01800000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing top interest stock data:
            - Stocks ranked by watchlist registration count
            - Popularity metrics

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_top_interest_stock(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Rank: {stock.get('rank')}, Stock: {stock.get('name')}")
    """
    api_id = "v1_국내주식-102"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/top-interest-stock"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_exp_trans_updown(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock expected conclusion up/down ranking.

    API ID: v1_국내주식-103
    Endpoint: /uapi/domestic-stock/v1/ranking/exp-trans-updown
    TR_ID: FHPST01820000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing expected conclusion up/down data:
            - Pre-market expected price movements
            - Top gainers and losers

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_exp_trans_updown(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Expected: {stock.get('expected_change')}")
    """
    api_id = "v1_국내주식-103"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/exp-trans-updown"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_traded_by_company(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stocks traded by their own companies (treasury stock).

    API ID: v1_국내주식-104
    Endpoint: /uapi/domestic-stock/v1/ranking/traded-by-company
    TR_ID: FHPST01860000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing company buyback ranking data:
            - Stocks being repurchased by issuing companies
            - Buyback volumes and amounts

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_traded_by_company(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Buyback: {stock.get('buyback_volume')}")
    """
    api_id = "v1_국내주식-104"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/traded-by-company"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_near_new_highlow(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stocks near new high/low prices.

    API ID: v1_국내주식-105
    Endpoint: /uapi/domestic-stock/v1/ranking/near-new-highlow
    TR_ID: FHPST01870000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing near new high/low data:
            - Stocks approaching 52-week high
            - Stocks approaching 52-week low
            - Distance to new highs/lows

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_near_new_highlow(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Type: {stock.get('type')}")
    """
    api_id = "v1_국내주식-105"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/near-new-highlow"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_quote_balance(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock ask/bid balance ranking.

    API ID: 국내주식-089
    Endpoint: /uapi/domestic-stock/v1/ranking/quote-balance
    TR_ID: FHPST01720000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing quote balance ranking data:
            - Order book imbalances
            - Buy/sell pressure indicators

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_quote_balance(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Balance: {stock.get('quote_balance')}")
    """
    api_id = "국내주식-089"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/quote-balance"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_dividend_rate(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock dividend rate ranking.

    API ID: 국내주식-106
    Endpoint: /uapi/domestic-stock/v1/ranking/dividend-rate
    TR_ID: HHKDB13470100 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing dividend rate ranking data:
            - Stocks ranked by dividend yield
            - Dividend amounts and dates

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_dividend_rate(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Dividend: {stock.get('dividend_rate')}%")
    """
    api_id = "국내주식-106"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/dividend-rate"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_bulk_trans_num(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock large transaction count ranking.

    API ID: 국내주식-107
    Endpoint: /uapi/domestic-stock/v1/ranking/bulk-trans-num
    TR_ID: FHKST190900C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing bulk transaction ranking data:
            - Stocks with large block trades
            - Transaction counts and sizes

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_bulk_trans_num(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Count: {stock.get('bulk_count')}")
    """
    api_id = "국내주식-107"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/bulk-trans-num"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_credit_balance(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock credit balance (margin trading) ranking.

    API ID: 국내주식-109
    Endpoint: /uapi/domestic-stock/v1/ranking/credit-balance
    TR_ID: FHKST17010000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing credit balance ranking data:
            - Stocks with highest margin trading balances
            - Margin debt levels

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_credit_balance(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Credit: {stock.get('credit_balance')}")
    """
    api_id = "국내주식-109"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/credit-balance"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_short_sale(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock short selling ranking.

    API ID: 국내주식-133
    Endpoint: /uapi/domestic-stock/v1/ranking/short-sale
    TR_ID: FHPST04820000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing short sale ranking data:
            - Most shorted stocks
            - Short selling volumes and ratios

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_short_sale(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Short: {stock.get('short_volume')}")
    """
    api_id = "국내주식-133"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/short-sale"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_overtime_fluctuation(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock after-hours fluctuation rate ranking.

    API ID: 국내주식-138
    Endpoint: /uapi/domestic-stock/v1/ranking/overtime-fluctuation
    TR_ID: FHPST02340000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing after-hours fluctuation ranking data:
            - Price movements during extended hours
            - Top gainers/losers in after-hours session

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_overtime_fluctuation(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Change: {stock.get('fluctuation_rate')}%")
    """
    api_id = "국내주식-138"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/overtime-fluctuation"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_overtime_volume(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve domestic stock after-hours trading volume ranking.

    API ID: 국내주식-139
    Endpoint: /uapi/domestic-stock/v1/ranking/overtime-volume
    TR_ID: FHPST02350000 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing after-hours volume ranking data:
            - Trading volumes during extended hours
            - Most active after-hours stocks

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_overtime_volume(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Stock: {stock.get('name')}, Volume: {stock.get('overtime_volume')}")
    """
    api_id = "국내주식-139"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/overtime-volume"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )


def get_hts_top_view(
    client: Any,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Retrieve HTS (Home Trading System) most viewed top 20 stocks.

    API ID: 국내주식-214
    Endpoint: /uapi/domestic-stock/v1/ranking/hts-top-view
    TR_ID: HHMCM000100C0 (Real only - Paper trading NOT supported)

    Args:
        client: KISRestClient instance for making API requests
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional query parameters

    Returns:
        Dictionary containing HTS top view data:
            - Top 20 most viewed stocks on HTS
            - View counts or rankings

    Raises:
        ValueError: If paper trading is requested (not supported)
        requests.exceptions.RequestException: If the API request fails

    Examples:
        >>> result = get_hts_top_view(client)
        >>> if result['rt_cd'] == '0':
        ...     for stock in result.get('output', []):
        ...         print(f"Rank: {stock.get('rank')}, Stock: {stock.get('name')}")
    """
    api_id = "국내주식-214"
    tr_id = _get_tr_id(api_id, is_paper_trading)

    path = f"{_RANKING_BASE}/hts-top-view"
    headers = {"tr_id": tr_id}

    params = {**kwargs}

    return client.make_request(
        method="GET",
        path=path,
        params=params,
        headers=headers,
    )
