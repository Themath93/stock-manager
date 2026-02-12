"""
KIS (Korea Investment & Securities) Domestic Stock Orders API

This module provides functions for interacting with KIS OpenAPI domestic stock
order and account management endpoints.

APIs included:
- Buy/Sell orders (cash, credit)
- Order cancellation and modification
- Order inquiries
- Account balance inquiries
- Pension-related inquiries
"""

from typing import Any, Dict, Literal, Optional


INQUIRE_BALANCE_DEFAULT_PARAMS: Dict[str, str] = {
    "AFHR_FLPR_YN": "N",
    "OFL_YN": "",
    "INQR_DVSN": "01",
    "UNPR_DVSN": "01",
    "FUND_STTL_ICLD_YN": "N",
    "FNCG_AMT_AUTO_RDPT_YN": "N",
    "PRCS_DVSN": "00",
    "CTX_AREA_FK100": "",
    "CTX_AREA_NK100": "",
}


def get_default_inquire_balance_params() -> Dict[str, str]:
    """Return a copy of default query params for inquire_balance."""
    return dict(INQUIRE_BALANCE_DEFAULT_PARAMS)


def get_tr_id_cash_order(order_type: Literal["buy", "sell"], is_paper_trading: bool = False) -> str:
    """
    Get TR_ID for cash order API.

    Args:
        order_type: Order type - "buy" for buy order, "sell" for sell order
        is_paper_trading: Whether to use paper trading (default: False)

    Returns:
        TR_ID string for the specified trading environment and order type

    Examples:
        >>> get_tr_id_cash_order("buy", is_paper_trading=False)
        'TTTC0012U'
        >>> get_tr_id_cash_order("sell", is_paper_trading=True)
        'VTTC0011U'
    """
    if is_paper_trading:
        return "VTTC0012U" if order_type == "buy" else "VTTC0011U"
    return "TTTC0012U" if order_type == "buy" else "TTTC0011U"


def get_tr_id_credit_order(order_type: Literal["buy", "sell"]) -> str:
    """
    Get TR_ID for credit order API.

    Note:
        Paper trading is not supported for credit orders.

    Args:
        order_type: Order type - "buy" for buy order, "sell" for sell order

    Returns:
        TR_ID string for credit orders (real trading only)

    Raises:
        ValueError: If attempting to use paper trading

    Examples:
        >>> get_tr_id_credit_order("buy")
        'TTTC0052U'
    """
    return "TTTC0052U" if order_type == "buy" else "TTTC0051U"


def cash_order(
    cano: str,
    acnt_prdt_cd: str,
    pdno: str,
    ord_dv: str,
    ord_qty: int,
    ord_unsl: str,
    order_type: Literal["buy", "sell"] = "buy",
    ord_prc: Optional[int] = None,
    tr_id: Optional[str] = None,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Place a cash order for domestic stocks (buy or sell).

    Notes:
        This helper now emits request-body keys aligned with KIS MCP examples:
        `ORD_DVSN`, `ORD_UNPR`, and `EXCG_ID_DVSN_CD`.
        Legacy arguments (`ord_dv`, `ord_prc`, `ord_unsl`) are preserved for
        backward compatibility and translated to the new keys.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol)
        ord_dv: Legacy order division (translated to ORD_DVSN)
        ord_qty: Order quantity
        ord_unsl: Legacy order unit argument (kept for compatibility)
        order_type: Order side - "buy" for buy order, "sell" for sell order (default: "buy")
        ord_prc: Legacy order price argument (translated to ORD_UNPR)
        tr_id: Custom TR_ID (if None, determined by is_paper_trading and order_type)
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API. Supported aliases:
            - ord_dvsn: explicit order division (overrides ord_dv)
            - ord_unpr: explicit order unit price (overrides ord_prc)
            - excg_id_dvsn_cd: exchange code (default "KRX")
            - sll_type, cndt_pric

    Returns:
        API response as dictionary containing order result

    Raises:
        ValueError: If required parameters are missing or invalid

    Examples:
        >>> # Buy 10 shares at market price
        >>> response = cash_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     ord_dv="01",
        ...     ord_qty=10,
        ...     ord_unsl="01",
        ...     order_type="buy",
        ...     is_paper_trading=True,
        ... )
        >>> # Sell 10 shares at 80,000 KRW (limit order)
        >>> response = cash_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     ord_dv="00",
        ...     ord_qty=10,
        ...     ord_unsl="01",
        ...     order_type="sell",
        ...     ord_prc=80000,
        ...     is_paper_trading=False,
        ... )
    """
    if tr_id is None:
        tr_id = get_tr_id_cash_order(order_type, is_paper_trading)

    resolved_ord_dvsn = str(kwargs.pop("ord_dvsn", ord_dv))
    if not resolved_ord_dvsn:
        raise ValueError("ord_dv/ord_dvsn must not be empty")

    resolved_ord_unpr = kwargs.pop("ord_unpr", ord_prc)
    if resolved_ord_unpr is None:
        resolved_ord_unpr = 0

    excg_id_dvsn_cd = str(kwargs.pop("excg_id_dvsn_cd", "KRX") or "KRX")
    sll_type = kwargs.pop("sll_type", "")
    cndt_pric = kwargs.pop("cndt_pric", "")

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": pdno,
        "ORD_DVSN": resolved_ord_dvsn,
        "ORD_QTY": str(ord_qty),
        "ORD_UNPR": str(resolved_ord_unpr),
        "EXCG_ID_DVSN_CD": excg_id_dvsn_cd,
        **kwargs,
    }
    if sll_type:
        params["SLL_TYPE"] = str(sll_type)
    if cndt_pric:
        params["CNDT_PRIC"] = str(cndt_pric)

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-cash",
        "params": params,
    }


def credit_order(
    cano: str,
    acnt_prdt_cd: str,
    pdno: str,
    ord_dv: str,
    ord_qty: int,
    ord_unsl: str,
    order_type: Literal["buy", "sell"] = "buy",
    ord_prc: Optional[int] = None,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Place a credit order for domestic stocks (buy or sell).

    Note:
        Paper trading is not supported for credit orders.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol)
        ord_dv: Order division - "00": limit order, "01": market order
        ord_qty: Order quantity
        ord_unsl: Order unit - "01": shares, "02": amount (KRW)
        order_type: Order side - "buy" for buy order, "sell" for sell order (default: "buy")
        ord_prc: Order price (required for limit orders)
        tr_id: Custom TR_ID (if None, determined automatically based on order_type)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing order result

    Raises:
        ValueError: If required parameters are missing

    Examples:
        >>> # Credit buy order
        >>> response = credit_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     ord_dv="01",
        ...     ord_qty=10,
        ...     ord_unsl="01",
        ...     order_type="buy",
        ... )
        >>> # Credit sell order
        >>> response = credit_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     ord_dv="00",
        ...     ord_qty=10,
        ...     ord_unsl="01",
        ...     order_type="sell",
        ...     ord_prc=80000,
        ... )
    """
    if tr_id is None:
        tr_id = get_tr_id_credit_order(order_type)

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": pdno,
        "ORD_DV": ord_dv,
        "ORD_QTY": str(ord_qty),
        "ORD_UNSL": ord_unsl,
        **kwargs,
    }

    if ord_prc is not None:
        params["ORD_PRC"] = str(ord_prc)

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-credit",
        "params": params,
    }


def order_cancel(
    cano: str,
    acnt_prdt_cd: str,
    orgn_odno: str,
    orgn_ord_dv: str,
    tr_id: Optional[str] = None,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Cancel or modify an existing domestic stock order.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        orgn_odno: Original order number
        orgn_ord_dv: Original order division
        tr_id: Custom TR_ID (if None, determined by is_paper_trading)
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing cancellation result

    Examples:
        >>> response = order_cancel(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     orgn_odno="0000012345",
        ...     orgn_ord_dv="00",
        ...     is_paper_trading=True,
        ... )
    """
    if tr_id is None:
        tr_id = "VTTC0013U" if is_paper_trading else "TTTC0013U"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "ORGN_ODNO": orgn_odno,
        "ORGN_ORD_DV": orgn_ord_dv,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-rvsecncl",
        "params": params,
    }


def inquire_psbl_rvsecncl(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire orders that can be revised or cancelled.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC0084R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing revisable/cancellable orders

    Examples:
        >>> response = inquire_psbl_rvsecncl(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC0084R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
        "params": params,
    }


def inquire_daily_ccld(
    cano: str,
    acnt_prdt_cd: str,
    ord_dt: str,
    tr_id: Optional[str] = None,
    is_paper_trading: bool = False,
    is_old_period: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire daily order conclusion (execution) details.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        ord_dt: Order date (YYYYMMDD format)
        tr_id: Custom TR_ID (if None, determined by is_paper_trading and is_old_period)
        is_paper_trading: Whether to use paper trading environment (default: False)
        is_old_period: Whether to query old period data (> 3 months) (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing daily order conclusion details

    Examples:
        >>> # Recent period (within 3 months)
        >>> response = inquire_daily_ccld(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     ord_dt="20240115",
        ...     is_paper_trading=True,
        ... )
        >>> # Old period (more than 3 months ago)
        >>> response = inquire_daily_ccld(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     ord_dt="20231001",
        ...     is_old_period=True,
        ... )
    """
    if tr_id is None:
        if is_old_period:
            tr_id = "VTSC9215R" if is_paper_trading else "CTSC9215R"
        else:
            tr_id = "VTTC0081R" if is_paper_trading else "TTTC0081R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "ORD_DT": ord_dt,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
        "params": params,
    }


def inquire_balance(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire domestic stock balance (holdings).

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, determined by is_paper_trading)
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing stock balance information

    Examples:
        >>> response = inquire_balance(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     is_paper_trading=True,
        ... )
    """
    if tr_id is None:
        tr_id = "VTTC8434R" if is_paper_trading else "TTTC8434R"

    query_params = get_default_inquire_balance_params()
    query_params.update(kwargs)

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **query_params,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-balance",
        "params": params,
    }


def inquire_balance_rlz_pl(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire domestic stock balance with realized profit/loss.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC8494R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing balance with realized profit/loss

    Examples:
        >>> response = inquire_balance_rlz_pl(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC8494R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl",
        "params": params,
    }


def inquire_psbl_order(
    cano: str,
    acnt_prdt_cd: str,
    pdno: Optional[str] = None,
    tr_id: Optional[str] = None,
    is_paper_trading: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire buyable quantity (cash).

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol) - optional
        tr_id: Custom TR_ID (if None, determined by is_paper_trading)
        is_paper_trading: Whether to use paper trading environment (default: False)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing buyable quantity information

    Examples:
        >>> response = inquire_psbl_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     is_paper_trading=True,
        ... )
    """
    if tr_id is None:
        tr_id = "VTTC8908R" if is_paper_trading else "TTTC8908R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    if pdno is not None:
        params["PDNO"] = pdno

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-psbl-order",
        "params": params,
    }


def inquire_psbl_sell(
    cano: str,
    acnt_prdt_cd: str,
    pdno: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire sellable quantity.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol)
        tr_id: Custom TR_ID (if None, uses TTTC8408R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing sellable quantity information

    Examples:
        >>> response = inquire_psbl_sell(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC8408R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": pdno,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-psbl-sell",
        "params": params,
    }


def inquire_credit_psamount(
    cano: str,
    acnt_prdt_cd: str,
    pdno: Optional[str] = None,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire credit buyable quantity.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol) - optional
        tr_id: Custom TR_ID (if None, uses TTTC8909R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing credit buyable quantity

    Examples:
        >>> response = inquire_credit_psamount(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC8909R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    if pdno is not None:
        params["PDNO"] = pdno

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-credit-psamount",
        "params": params,
    }


def order_resv(
    cano: str,
    acnt_prdt_cd: str,
    pdno: str,
    ord_dv: str,
    ord_qty: int,
    ord_unsl: str,
    ord_prc: Optional[int] = None,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Place a reservation order for domestic stocks.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol)
        ord_dv: Order division - "00": limit order, "01": market order
        ord_qty: Order quantity
        ord_unsl: Order unit - "01": shares, "02": amount (KRW)
        ord_prc: Order price (required for limit orders)
        tr_id: Custom TR_ID (if None, uses CTSC0008U)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing reservation order result

    Examples:
        >>> response = order_resv(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ...     ord_dv="01",
        ...     ord_qty=10,
        ...     ord_unsl="01",
        ... )
    """
    if tr_id is None:
        tr_id = "CTSC0008U"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": pdno,
        "ORD_DV": ord_dv,
        "ORD_QTY": str(ord_qty),
        "ORD_UNSL": ord_unsl,
        **kwargs,
    }

    if ord_prc is not None:
        params["ORD_PRC"] = str(ord_prc)

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-resv",
        "params": params,
    }


def order_resv_rvsecncl(
    cano: str,
    acnt_prdt_cd: str,
    orgn_odno: str,
    rvse_cncl_dv: Literal["cancel", "revise"],
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Cancel or modify a reservation order.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        orgn_odno: Original order number
        rvse_cncl_dv: Revision/cancellation division - "cancel": cancel, "revise": revise
        tr_id: Custom TR_ID (if None, determined by rvse_cncl_dv)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing revision/cancellation result

    Examples:
        >>> # Cancel reservation order
        >>> response = order_resv_rvsecncl(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     orgn_odno="0000012345",
        ...     rvse_cncl_dv="cancel",
        ... )
        >>> # Revise reservation order
        >>> response = order_resv_rvsecncl(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     orgn_odno="0000012345",
        ...     rvse_cncl_dv="revise",
        ... )
    """
    if tr_id is None:
        tr_id = "CTSC0009U" if rvse_cncl_dv == "cancel" else "CTSC0013U"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "ORGN_ODNO": orgn_odno,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-resv-rvsecncl",
        "params": params,
    }


def order_resv_ccnl(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire reservation orders.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses CTSC0004R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing reservation order information

    Examples:
        >>> response = order_resv_ccnl(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "CTSC0004R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/order-resv-ccnl",
        "params": params,
    }


def pension_inquire_present_balance(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire pension account present balance (conclusion-based).

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC2202R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing pension present balance

    Examples:
        >>> response = pension_inquire_present_balance(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC2202R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/pension/inquire-present-balance",
        "params": params,
    }


def pension_inquire_daily_ccld(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    use_nxt: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire pension account daily conclusion (unexecuted orders).

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, determined by use_nxt)
        use_nxt: Whether to use NXT/SOR exchange (default: False for KRX only)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing pension daily conclusion

    Examples:
        >>> # KRX only (traditional)
        >>> response = pension_inquire_daily_ccld(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     use_nxt=False,
        ... )
        >>> # KRX, NXT/SOR
        >>> response = pension_inquire_daily_ccld(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     use_nxt=True,
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC2210R" if use_nxt else "TTTC2201R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld",
        "params": params,
    }


def pension_inquire_psbl_order(
    cano: str,
    acnt_prdt_cd: str,
    pdno: Optional[str] = None,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire pension account buyable quantity.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        pdno: Product code (stock symbol) - optional
        tr_id: Custom TR_ID (if None, uses TTTC0503R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing pension buyable quantity

    Examples:
        >>> response = pension_inquire_psbl_order(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     pdno="005930",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC0503R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    if pdno is not None:
        params["PDNO"] = pdno

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order",
        "params": params,
    }


def pension_inquire_deposit(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire pension account deposit.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC0506R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing pension deposit information

    Examples:
        >>> response = pension_inquire_deposit(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC0506R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/pension/inquire-deposit",
        "params": params,
    }


def pension_inquire_balance(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire pension account balance.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC2208R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing pension balance information

    Examples:
        >>> response = pension_inquire_balance(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC2208R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/pension/inquire-balance",
        "params": params,
    }


def inquire_account_balance(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire investment account asset status.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses CTRP6548R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing account asset status

    Examples:
        >>> response = inquire_account_balance(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "CTRP6548R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-account-balance",
        "params": params,
    }


def inquire_period_profit(
    cano: str,
    acnt_prdt_cd: str,
    str_dt: str,
    end_dt: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire period profit/loss daily summary.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        str_dt: Start date (YYYYMMDD format)
        end_dt: End date (YYYYMMDD format)
        tr_id: Custom TR_ID (if None, uses TTTC8708R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing period profit/loss summary

    Examples:
        >>> response = inquire_period_profit(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     str_dt="20240101",
        ...     end_dt="20240131",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC8708R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "STR_DT": str_dt,
        "END_DT": end_dt,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-period-profit",
        "params": params,
    }


def inquire_period_trade_profit(
    cano: str,
    acnt_prdt_cd: str,
    str_dt: str,
    end_dt: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire period trading profit/loss status.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        str_dt: Start date (YYYYMMDD format)
        end_dt: End date (YYYYMMDD format)
        tr_id: Custom TR_ID (if None, uses TTTC8715R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing period trading profit/loss

    Examples:
        >>> response = inquire_period_trade_profit(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     str_dt="20240101",
        ...     end_dt="20240131",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC8715R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "STR_DT": str_dt,
        "END_DT": end_dt,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/inquire-period-trade-profit",
        "params": params,
    }


def intgr_margin(
    cano: str,
    acnt_prdt_cd: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire integrated margin status.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        tr_id: Custom TR_ID (if None, uses TTTC0869R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing integrated margin status

    Examples:
        >>> response = intgr_margin(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ... )
    """
    if tr_id is None:
        tr_id = "TTTC0869R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/intgr-margin",
        "params": params,
    }


def period_rights(
    cano: str,
    acnt_prdt_cd: str,
    str_dt: str,
    end_dt: str,
    tr_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Inquire period account rights status.

    Note:
        Paper trading is not supported for this API.

    Args:
        cano: Account number (8 digits)
        acnt_prdt_cd: Account product code (2 digits)
        str_dt: Start date (YYYYMMDD format)
        end_dt: End date (YYYYMMDD format)
        tr_id: Custom TR_ID (if None, uses CTRGA011R)
        **kwargs: Additional parameters for the API

    Returns:
        API response as dictionary containing period account rights status

    Examples:
        >>> response = period_rights(
        ...     cano="12345678",
        ...     acnt_prdt_cd="01",
        ...     str_dt="20240101",
        ...     end_dt="20240131",
        ... )
    """
    if tr_id is None:
        tr_id = "CTRGA011R"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "STR_DT": str_dt,
        "END_DT": end_dt,
        **kwargs,
    }

    return {
        "tr_id": tr_id,
        "url_path": "/uapi/domestic-stock/v1/trading/period-rights",
        "params": params,
    }
