"""
KIS (Korea Investment & Securities) Overseas Stock Analysis/Ranking API Functions.

This module provides functions for accessing overseas stock analysis data including
price fluctuations, volume rankings, and market indicators.

API Reference: https://apiportal.koreainvestment.com/
"""

from typing import Any, Dict, Literal


def get_overseas_price_fluctuation(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks with rapid price changes (up/down).

    This function retrieves a list of overseas stocks showing significant
    price increases or decreases.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - List of stocks with price fluctuations
            - Price change percentages
            - Trading volumes

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_price_fluctuation(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-038
        - Real TR_ID: HHDFS76260000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/price-fluct
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76260000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
        "FID_COND_SCR_DIV_CODE": "N",  # N: New
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/price-fluct",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_volume_surge(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks with rapidly increasing trading volume.

    This function retrieves a list of overseas stocks showing significant
    increases in trading volume compared to their average.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - List of stocks with volume surges
            - Volume increase percentages
            - Current trading volumes

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_volume_surge(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-039
        - Real TR_ID: HHDFS76270000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/volume-surge
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76270000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/volume-surge",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_volume_power(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by buying volume strength.

    This function retrieves overseas stocks with strong buying pressure
    based on volume analysis.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by buying volume power
            - Volume strength indicators
            - Buy/sell ratios

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_volume_power(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-040
        - Real TR_ID: HHDFS76280000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/volume-power
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76280000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/volume-power",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_updown_rate(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by increase/decrease rate.

    This function retrieves overseas stocks ranked by their percentage
    increase or decrease.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by change percentage
            - Increase/decrease rates
            - Price change amounts

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_updown_rate(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-041
        - Real TR_ID: HHDFS76290000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/updown-rate
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76290000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/updown-rate",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_new_highlow(
    client: Any,
    market_code: str,
    period_type: Literal["D", "W", "M", "Y"] = "D",
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks hitting new highs or new lows.

    This function retrieves overseas stocks that have reached new price
    highs or lows for the specified period.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        period_type: Period type for new high/low calculation.
            'D' for daily, 'W' for weekly, 'M' for monthly, 'Y' for yearly.
            Defaults to 'D' (daily).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks hitting new highs
            - Stocks hitting new lows
            - New high/low prices

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_new_highlow(
        ...     client=client,
        ...     market_code="NASD",
        ...     period_type="D",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-042
        - Real TR_ID: HHDFS76300000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/new-highlow
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76300000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
        "FID_NEW_HL_LST_YN": "Y",  # Y: List new highs/lows
        "FID_COND_SCR_DIV_CODE": period_type,  # D, W, M, Y
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/new-highlow",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_trade_volume_ranking(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by trading volume.

    This function retrieves overseas stocks ranked by their trading volume.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by trading volume
            - Trading volume amounts
            - Volume rankings

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_trade_volume_ranking(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-043
        - Real TR_ID: HHDFS76310010
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/trade-vol
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76310010"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/trade-vol",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_trade_amount_ranking(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by trading amount (value).

    This function retrieves overseas stocks ranked by their total trading
    amount (volume × price).

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by trading amount
            - Trading amounts
            - Amount rankings

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_trade_amount_ranking(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-044
        - Real TR_ID: HHDFS76320010
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/trade-pbmn
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76320010"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/trade-pbmn",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_trade_growth_ranking(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by trading amount growth rate.

    This function retrieves overseas stocks ranked by their trading amount
    increase rate compared to previous periods.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by trading growth
            - Growth rate percentages
            - Trading amount comparisons

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_trade_growth_ranking(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-045
        - Real TR_ID: HHDFS76330000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/trade-growth
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76330000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/trade-growth",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_turnover_ranking(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by trading turnover rate.

    This function retrieves overseas stocks ranked by their turnover rate,
    which indicates how actively the stock is being traded.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by turnover rate
            - Turnover rate percentages
            - Turnover rankings

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_turnover_ranking(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-046
        - Real TR_ID: HHDFS76340000
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/trade-turnover
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76340000"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/trade-turnover",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_market_cap_ranking(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks ranked by market capitalization.

    This function retrieves overseas stocks ranked by their total market
    capitalization value.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE', 'TKSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Stocks ranked by market cap
            - Market capitalization values
            - Market cap rankings

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_market_cap_ranking(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-047
        - Real TR_ID: HHDFS76350100
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-stock/v1/ranking/market-cap
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS76350100"

    params = {
        "FID_COND_MRKT_DIV_CODE": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-stock/v1/ranking/market-cap",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_rights_summary(
    client: Any,
    symbol: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get rights (dividends, splits, etc.) summary for an overseas stock.

    This function retrieves comprehensive rights information including dividends,
    stock splits, and other corporate actions.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Dividend information
            - Stock split history
            - Other corporate actions

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_rights_summary(
        ...     client=client,
        ...     symbol="AAPL",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-050
        - Real TR_ID: HHDFS78330900
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/rights-by-ice
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHDFS78330900"

    params = {
        "SRT": "00",  # Sort (00: recent, 01: past)
        "symbol": symbol,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/rights-by-ice",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_period_rights(
    client: Any,
    symbol: str,
    start_date: str,
    end_date: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get rights information for a specific period for an overseas stock.

    This function retrieves detailed rights information for a specified
    date range including dividends and corporate actions.

    Args:
        client: KISRestClient instance for making API requests.
        symbol: Overseas stock symbol (e.g., 'AAPL' for Apple).
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing detailed rights information
            for the specified period.

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_period_rights(
        ...     client=client,
        ...     symbol="AAPL",
        ...     start_date="20240101",
        ...     end_date="20241231",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-052
        - Real TR_ID: CTRGT011R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/period-rights
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTRGT011R"

    params = {
        "symbol": symbol,
        "strt_dt": start_date,
        "end_dt": end_date,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/period-rights",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_collateral_stocks(
    client: Any,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas stocks eligible for company collateral loans.

    This function retrieves a list of overseas stocks that can be used as
    collateral for loans at Korea Investment & Securities.

    Args:
        client: KISRestClient instance for making API requests.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - List of eligible stocks
            - Loan-to-value ratios
            - Eligibility conditions

    Raises:
        ValueError: If paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_collateral_stocks(
        ...     client=client,
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-051
        - Real TR_ID: CTLN4050R
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/colable-by-company
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "CTLN4050R"

    params = {}

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/colable-by-company",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_news_titles(
    client: Any,
    market_code: str,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas news titles by market.

    This function retrieves recent news headlines for overseas markets.

    Args:
        client: KISRestClient instance for making API requests.
        market_code: Market code (e.g., 'NASD', 'NYSE').
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - News headlines
            - Publication times
            - News sources

    Raises:
        ValueError: If required parameters are invalid or paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_news_titles(
        ...     client=client,
        ...     market_code="NASD",
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-053
        - Real TR_ID: HHPSTH60100C1
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/news-title
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "HHPSTH60100C1"

    params = {
        "MKT_ID": market_code,
    }

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/news-title",
        params=params,
        headers={"tr_id": tr_id},
    )


def get_overseas_breaking_news(
    client: Any,
    is_paper_trading: bool = False,
) -> Dict[str, Any]:
    """
    Get overseas breaking news titles.

    This function retrieves recent breaking news headlines for overseas markets.

    Args:
        client: KISRestClient instance for making API requests.
        is_paper_trading: Whether to use paper trading (True) or real trading (False).
            Note: Paper trading is NOT supported for this API.
            Defaults to False.

    Returns:
        Dict[str, Any]: API response containing:
            - Breaking news headlines
            - Publication times
            - News categories

    Raises:
        ValueError: If paper trading is requested.
        ConnectionError: If connection to KIS API fails.

    Examples:
        >>> response = get_overseas_breaking_news(
        ...     client=client,
        ...     is_paper_trading=False
        ... )

    Notes:
        - API ID: 해외주식-055
        - Real TR_ID: FHKST01011801
        - Paper TR_ID: Not Supported
        - URL: /uapi/overseas-price/v1/quotations/brknews-title
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for this API")

    tr_id = "FHKST01011801"

    params = {}

    return client.make_request(
        method="GET",
        path="/uapi/overseas-price/v1/quotations/brknews-title",
        params=params,
        headers={"tr_id": tr_id},
    )


# URL constants for reference
OVERSEAS_RANKING_BASE_PATH = "/uapi/overseas-stock/v1/ranking"
OVERSEAS_QUOTES_BASE_PATH = "/uapi/overseas-price/v1/quotations"


def get_overseas_analysis_api_url(
    endpoint: str,
    base_path: str = OVERSEAS_RANKING_BASE_PATH,
) -> str:
    """
    Get the full URL for an overseas stock analysis API endpoint.

    Args:
        endpoint: The API endpoint path.
        base_path: Base path for the API (ranking or quotations).
            Defaults to OVERSEAS_RANKING_BASE_PATH.

    Returns:
        str: The complete URL path for the specified endpoint.

    Examples:
        >>> url = get_overseas_analysis_api_url("/price-fluct")
        >>> print(url)
        /uapi/overseas-stock/v1/ranking/price-fluct
    """
    return f"{base_path}{endpoint}"
