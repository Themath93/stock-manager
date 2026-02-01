"""
Domestic Stock Realtime API Functions for KIS (Korea Investment & Securities) OpenAPI.

This module provides functions for interacting with KIS OpenAPI domestic stock
real-time endpoints using WebSocket communication.

APIs included:
- Real-time expected conclusion (NXT, Integrated, KRX)
- Real-time execution price (NXT, Integrated, KRX)
- Real-time program trading (NXT, Integrated, KRX)
- Real-time quote/ask prices (NXT, Integrated, KRX)
- Real-time member company trading (NXT, Integrated, KRX)
- Market operation information (NXT, Integrated, KRX)
- Index real-time data
- After-hours real-time data
- ELW real-time data
- ETF NAV trends
"""

from typing import Any, Dict, Optional


# TR_ID Constants for Real-time APIs
TR_IDS = {
    # NXT APIs (Real trading only)
    "H0NXANC0": {"real": "H0NXANC0", "paper": None},  # Expected conclusion
    "H0NXCNT0": {"real": "H0NXCNT0", "paper": None},  # Execution price
    "H0NXPGM0": {"real": "H0NXPGM0", "paper": None},  # Program trading
    "H0NXASP0": {"real": "H0NXASP0", "paper": None},  # Quote/ask prices
    "H0NXMBC0": {"real": "H0NXMBC0", "paper": None},  # Member company trading
    "H0NXMKO0": {"real": "H0NXMKO0", "paper": None},  # Market operation info

    # Integrated APIs (Real trading only)
    "H0UNANC0": {"real": "H0UNANC0", "paper": None},  # Expected conclusion
    "H0UNCNT0": {"real": "H0UNCNT0", "paper": None},  # Execution price
    "H0UNPGM0": {"real": "H0UNPGM0", "paper": None},  # Program trading
    "H0UNASP0": {"real": "H0UNASP0", "paper": None},  # Quote/ask prices
    "H0UNMBC0": {"real": "H0UNMBC0", "paper": None},  # Member company trading
    "H0UNMKO0": {"real": "H0UNMKO0", "paper": None},  # Market operation info

    # KRX APIs (Most real trading only, some support both)
    "H0STCNT0": {"real": "H0STCNT0", "paper": "H0STCNT0"},  # Execution price (both)
    "H0STASP0": {"real": "H0STASP0", "paper": "H0STASP0"},  # Quote/ask prices (both)
    "H0STCNI0": {"real": "H0STCNI0", "paper": "H0STCNI9"},  # Execution notice
    "H0STANC0": {"real": "H0STANC0", "paper": None},  # Expected conclusion
    "H0STOAC0": {"real": "H0STOAC0", "paper": None},  # After-hours expected conclusion
    "H0STOAA0": {"real": "H0STOAA0", "paper": None},  # After-hours quote/ask prices
    "H0STOUP0": {"real": "H0STOUP0", "paper": None},  # After-hours execution price
    "H0STMBC0": {"real": "H0STMBC0", "paper": None},  # Member company trading
    "H0STPGM0": {"real": "H0STPGM0", "paper": None},  # Program trading
    "H0STMKO0": {"real": "H0STMKO0", "paper": None},  # Market operation info

    # Index APIs (Real trading only)
    "H0UPCNT0": {"real": "H0UPCNT0", "paper": None},  # Index execution
    "H0UPANC0": {"real": "H0UPANC0", "paper": None},  # Index expected conclusion
    "H0UPPGM0": {"real": "H0UPPGM0", "paper": None},  # Index program trading

    # ETF/ELW APIs (Real trading only)
    "H0STNAV0": {"real": "H0STNAV0", "paper": None},  # ETF NAV trend
    "H0EWCNT0": {"real": "H0EWCNT0", "paper": None},  # ELW execution price
    "H0EWASP0": {"real": "H0EWASP0", "paper": None},  # ELW quote/ask prices
    "H0EWANC0": {"real": "H0EWANC0", "paper": None},  # ELW expected conclusion
}


def _get_tr_id(tr_id_key: str, is_paper_trading: bool = False) -> str:
    """
    Get the appropriate TR_ID for the given API and trading environment.

    Args:
        tr_id_key: The TR_ID key (e.g., 'H0NXANC0')
        is_paper_trading: Whether to use paper trading TR_ID

    Returns:
        The TR_ID string for the specified environment

    Raises:
        ValueError: If paper trading is not supported for the API
    """
    if tr_id_key not in TR_IDS:
        raise ValueError(f"Unknown TR_ID key: {tr_id_key}")

    tr_id_info = TR_IDS[tr_id_key]

    if is_paper_trading:
        if tr_id_info["paper"] is None:
            raise ValueError(f"Paper trading is not supported for {tr_id_key}")
        return tr_id_info["paper"]

    return tr_id_info["real"]


def get_H0NXANC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time expected conclusion for domestic stocks (NXT).

    API ID: 국내주식 실시간예상체결 (NXT)
    TR_ID: H0NXANC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time expected conclusion data with:
            - rt_cd: Return code ('0' for success)
            - msg_cd: Message code
            - msg1: Message description
            - output: Expected conclusion data including price, volume

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXANC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
        Only real trading is available.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXANC0")

    tr_id = _get_tr_id("H0NXANC0", is_paper_trading=False)
    path = "/tryitout/H0NXANC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNANC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time expected conclusion for domestic stocks (Integrated).

    API ID: 국내주식 실시간예상체결 (통합)
    TR_ID: H0UNANC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time expected conclusion data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNANC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNANC0")

    tr_id = _get_tr_id("H0UNANC0", is_paper_trading=False)
    path = "/tryitout/H0UNANC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0NXCNT0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution price for domestic stocks (NXT).

    API ID: 국내주식 실시간체결가 (NXT)
    TR_ID: H0NXCNT0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time execution price data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXCNT0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Execution price:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXCNT0")

    tr_id = _get_tr_id("H0NXCNT0", is_paper_trading=False)
    path = "/tryitout/H0NXCNT0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNCNT0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution price for domestic stocks (Integrated).

    API ID: 국내주식 실시간체결가 (통합)
    TR_ID: H0UNCNT0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time execution price data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNCNT0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Execution price:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNCNT0")

    tr_id = _get_tr_id("H0UNCNT0", is_paper_trading=False)
    path = "/tryitout/H0UNCNT0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0NXPGM0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time program trading data for domestic stocks (NXT).

    API ID: 국내주식 실시간프로그램매매 (NXT)
    TR_ID: H0NXPGM0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time program trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXPGM0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Program trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXPGM0")

    tr_id = _get_tr_id("H0NXPGM0", is_paper_trading=False)
    path = "/tryitout/H0NXPGM0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNPGM0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time program trading data for domestic stocks (Integrated).

    API ID: 국내주식 실시간프로그램매매 (통합)
    TR_ID: H0UNPGM0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time program trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNPGM0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Program trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNPGM0")

    tr_id = _get_tr_id("H0UNPGM0", is_paper_trading=False)
    path = "/tryitout/H0UNPGM0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0NXASP0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time quote/ask prices for domestic stocks (NXT).

    API ID: 국내주식 실시간호가 (NXT)
    TR_ID: H0NXASP0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time quote/ask prices data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXASP0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Quote/ask prices:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXASP0")

    tr_id = _get_tr_id("H0NXASP0", is_paper_trading=False)
    path = "/tryitout/H0NXASP0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNASP0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time quote/ask prices for domestic stocks (Integrated).

    API ID: 국내주식 실시간호가 (통합)
    TR_ID: H0UNASP0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time quote/ask prices data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNASP0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Quote/ask prices:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNASP0")

    tr_id = _get_tr_id("H0UNASP0", is_paper_trading=False)
    path = "/tryitout/H0UNASP0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0NXMBC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time member company trading data for domestic stocks (NXT).

    API ID: 국내주식 실시간회원사 (NXT)
    TR_ID: H0NXMBC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time member company trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXMBC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Member trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXMBC0")

    tr_id = _get_tr_id("H0NXMBC0", is_paper_trading=False)
    path = "/tryitout/H0NXMBC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNMBC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time member company trading data for domestic stocks (Integrated).

    API ID: 국내주식 실시간회원사 (통합)
    TR_ID: H0UNMBC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time member company trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNMBC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Member trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNMBC0")

    tr_id = _get_tr_id("H0UNMBC0", is_paper_trading=False)
    path = "/tryitout/H0UNMBC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0NXMKO0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve market operation information for domestic stocks (NXT).

    API ID: 국내주식 장운영정보 (NXT)
    TR_ID: H0NXMKO0 (Real only)
    Communication: REST

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing market operation information

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0NXMKO0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Market operation info:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0NXMKO0")

    tr_id = _get_tr_id("H0NXMKO0", is_paper_trading=False)
    path = "/tryitout/H0NXMKO0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UNMKO0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve market operation information for domestic stocks (Integrated).

    API ID: 국내주식 장운영정보 (통합)
    TR_ID: H0UNMKO0 (Real only)
    Communication: REST

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing market operation information

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UNMKO0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Market operation info:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UNMKO0")

    tr_id = _get_tr_id("H0UNMKO0", is_paper_trading=False)
    path = "/tryitout/H0UNMKO0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STCNT0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution price for domestic stocks (KRX).

    API ID: 실시간-003
    TR_ID: H0STCNT0 (Both real and paper trading)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time execution price data

    Examples:
        >>> result = get_H0STCNT0(client, is_paper_trading=True)
        >>> if result.get("rt_cd") == "0":
        ...     print("Execution price:", result.get("output"))
    """
    tr_id = _get_tr_id("H0STCNT0", is_paper_trading)
    path = "/tryitout/H0STCNT0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STASP0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time quote/ask prices for domestic stocks (KRX).

    API ID: 실시간-004
    TR_ID: H0STASP0 (Both real and paper trading)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time quote/ask prices data

    Examples:
        >>> result = get_H0STASP0(client, is_paper_trading=True)
        >>> if result.get("rt_cd") == "0":
        ...     print("Quote/ask prices:", result.get("output"))
    """
    tr_id = _get_tr_id("H0STASP0", is_paper_trading)
    path = "/tryitout/H0STASP0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STCNI0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution notice for domestic stocks.

    API ID: 실시간-005
    TR_ID: H0STCNI0 (Real), H0STCNI9 (Paper)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time execution notice data

    Examples:
        >>> result = get_H0STCNI0(client, is_paper_trading=True)
        >>> if result.get("rt_cd") == "0":
        ...     print("Execution notice:", result.get("output"))
    """
    tr_id = _get_tr_id("H0STCNI0", is_paper_trading)
    path = "/tryitout/H0STCNI0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STOAC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve after-hours real-time expected conclusion for domestic stocks (KRX).

    API ID: 실시간-024
    TR_ID: H0STOAC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing after-hours expected conclusion data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STOAC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("After-hours expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STOAC0")

    tr_id = _get_tr_id("H0STOAC0", is_paper_trading=False)
    path = "/tryitout/H0STOAC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STOAA0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve after-hours real-time quote/ask prices for domestic stocks (KRX).

    API ID: 실시간-025
    TR_ID: H0STOAA0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing after-hours quote/ask prices data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STOAA0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("After-hours quote/ask prices:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STOAA0")

    tr_id = _get_tr_id("H0STOAA0", is_paper_trading=False)
    path = "/tryitout/H0STOAA0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UPCNT0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution data for domestic indices.

    API ID: 실시간-026
    TR_ID: H0UPCNT0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time index execution data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UPCNT0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Index execution:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UPCNT0")

    tr_id = _get_tr_id("H0UPCNT0", is_paper_trading=False)
    path = "/tryitout/H0UPCNT0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UPANC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time expected conclusion for domestic indices.

    API ID: 실시간-027
    TR_ID: H0UPANC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time index expected conclusion data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UPANC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Index expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UPANC0")

    tr_id = _get_tr_id("H0UPANC0", is_paper_trading=False)
    path = "/tryitout/H0UPANC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0UPPGM0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time program trading data for domestic indices.

    API ID: 실시간-028
    TR_ID: H0UPPGM0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time index program trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0UPPGM0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Index program trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0UPPGM0")

    tr_id = _get_tr_id("H0UPPGM0", is_paper_trading=False)
    path = "/tryitout/H0UPPGM0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STANC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time expected conclusion for domestic stocks (KRX).

    API ID: 실시간-041
    TR_ID: H0STANC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time expected conclusion data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STANC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STANC0")

    tr_id = _get_tr_id("H0STANC0", is_paper_trading=False)
    path = "/tryitout/H0STANC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STOUP0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve after-hours real-time execution price for domestic stocks (KRX).

    API ID: 실시간-042
    TR_ID: H0STOUP0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing after-hours execution price data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STOUP0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("After-hours execution price:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STOUP0")

    tr_id = _get_tr_id("H0STOUP0", is_paper_trading=False)
    path = "/tryitout/H0STOUP0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STMBC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time member company trading data for domestic stocks (KRX).

    API ID: 실시간-047
    TR_ID: H0STMBC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time member company trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STMBC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Member trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STMBC0")

    tr_id = _get_tr_id("H0STMBC0", is_paper_trading=False)
    path = "/tryitout/H0STMBC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STPGM0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time program trading data for domestic stocks (KRX).

    API ID: 실시간-048
    TR_ID: H0STPGM0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time program trading data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STPGM0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Program trading:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STPGM0")

    tr_id = _get_tr_id("H0STPGM0", is_paper_trading=False)
    path = "/tryitout/H0STPGM0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STMKO0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve market operation information for domestic stocks (KRX).

    API ID: 실시간-049
    TR_ID: H0STMKO0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing market operation information

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STMKO0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("Market operation info:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STMKO0")

    tr_id = _get_tr_id("H0STMKO0", is_paper_trading=False)
    path = "/tryitout/H0STMKO0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0STNAV0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time NAV trend for domestic ETFs.

    API ID: 실시간-051
    TR_ID: H0STNAV0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time ETF NAV trend data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0STNAV0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("ETF NAV trend:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0STNAV0")

    tr_id = _get_tr_id("H0STNAV0", is_paper_trading=False)
    path = "/tryitout/H0STNAV0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0EWCNT0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time execution price for ELW (Equity Linked Warrants).

    API ID: 실시간-061
    TR_ID: H0EWCNT0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time ELW execution price data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0EWCNT0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("ELW execution price:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0EWCNT0")

    tr_id = _get_tr_id("H0EWCNT0", is_paper_trading=False)
    path = "/tryitout/H0EWCNT0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0EWASP0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time quote/ask prices for ELW (Equity Linked Warrants).

    API ID: 실시간-062
    TR_ID: H0EWASP0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time ELW quote/ask prices data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0EWASP0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("ELW quote/ask prices:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0EWASP0")

    tr_id = _get_tr_id("H0EWASP0", is_paper_trading=False)
    path = "/tryitout/H0EWASP0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )


def get_H0EWANC0(
    client: Any,
    is_paper_trading: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve real-time expected conclusion for ELW (Equity Linked Warrants).

    API ID: 실시간-063
    TR_ID: H0EWANC0 (Real only)
    Communication: WebSocket

    Args:
        client: KISRestClient or compatible client instance
        is_paper_trading: Whether to use paper trading environment (default: False)
        params: Optional dictionary of additional query parameters

    Returns:
        Dictionary containing real-time ELW expected conclusion data

    Raises:
        ValueError: If paper trading is requested (not supported)

    Examples:
        >>> result = get_H0EWANC0(client)
        >>> if result.get("rt_cd") == "0":
        ...     print("ELW expected conclusion:", result.get("output"))

    Note:
        Paper trading is not supported for this API.
    """
    if is_paper_trading:
        raise ValueError("Paper trading is not supported for H0EWANC0")

    tr_id = _get_tr_id("H0EWANC0", is_paper_trading=False)
    path = "/tryitout/H0EWANC0"

    headers = {"tr_id": tr_id}

    return client.make_request(
        method="POST",
        path=path,
        params=params or {},
        headers=headers,
    )
