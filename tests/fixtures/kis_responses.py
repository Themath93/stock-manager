"""
KIS API Response Fixtures for Testing

This module provides reusable mock API responses for KIS OpenAPI.
Includes fixtures for various API endpoints with realistic sample data.

KIS API Response Pattern:
{
    "rt_cd": "0",       # Return code ("0" = success, other = error)
    "msg_cd": "0",      # Message code
    "msg1": "OK",       # Message text
    "output": {...}     # Actual data payload
}
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================================
# Success Response Fixtures
# ============================================================================


def mock_inquire_balance_success() -> Dict[str, Any]:
    """
    Mock response for inquire_balance API with multiple positions.

    Includes realistic holdings for Samsung Electronics and SK Hynix.
    """
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output1": [
            {
                "pdno": "005930",  # Samsung Electronics
                "prdt_name": "삼성전자",
                "trad_dvsn_name": "현금",
                "bfdy_buy_qty": "10",
                "bfdy_sll_qty": "0",
                "thdt_buyqty": "0",
                "thdt_sll_qty": "0",
                "hldg_qty": "10",  # Holding quantity
                "ord_psbl_qty": "10",  # Orderable quantity
                "pchs_avg_pric": "70000.00",  # Average purchase price
                "pchs_amt": "700000",  # Purchase amount
                "prpr": "75000",  # Current price
                "evlu_amt": "750000",  # Evaluation amount
                "evlu_pfls_amt": "50000",  # Evaluation profit/loss
                "evlu_pfls_rt": "7.14",  # Evaluation profit/loss rate
                "evlu_erng_rt": "7.14",  # Evaluation earning rate
                "loan_dt": "",
                "loan_amt": "0",
                "stln_slng_chgs": "0",
                "expd_dt": "",
                "fltt_rt": "0.00",
                "bfdy_cprs_icdc": "2000",  # Compared to previous day
                "item_mgna_rt_name": "20%",
                "grta_rt_name": "",
                "sbst_pric": "75000",
                "stck_loan_unpr": "0.00"
            },
            {
                "pdno": "000660",  # SK Hynix
                "prdt_name": "SK하이닉스",
                "trad_dvsn_name": "현금",
                "bfdy_buy_qty": "5",
                "bfdy_sll_qty": "0",
                "thdt_buyqty": "0",
                "thdt_sll_qty": "0",
                "hldg_qty": "5",
                "ord_psbl_qty": "5",
                "pchs_avg_pric": "130000.00",
                "pchs_amt": "650000",
                "prpr": "135000",
                "evlu_amt": "675000",
                "evlu_pfls_amt": "25000",
                "evlu_pfls_rt": "3.85",
                "evlu_erng_rt": "3.85",
                "loan_dt": "",
                "loan_amt": "0",
                "stln_slng_chgs": "0",
                "expd_dt": "",
                "fltt_rt": "0.00",
                "bfdy_cprs_icdc": "3000",
                "item_mgna_rt_name": "40%",
                "grta_rt_name": "",
                "sbst_pric": "135000",
                "stck_loan_unpr": "0.00"
            }
        ],
        "output2": [
            {
                "dnca_tot_amt": "10000000",  # Total deposit
                "nxdy_excc_amt": "8575000",  # Next day excess amount
                "prvs_rcdl_excc_amt": "8575000",  # Previous record excess
                "cma_evlu_amt": "0",
                "bfdy_buy_amt": "0",
                "thdt_buy_amt": "0",
                "nxdy_auto_rdpt_amt": "0",
                "bfdy_sll_amt": "0",
                "thdt_sll_amt": "0",
                "d2_auto_rdpt_amt": "0",
                "bfdy_tlex_amt": "0",
                "thdt_tlex_amt": "0",
                "tot_loan_amt": "0",
                "scts_evlu_amt": "1425000",  # Securities evaluation amount
                "tot_evlu_amt": "11425000",  # Total evaluation amount
                "nass_amt": "11425000",  # Net asset amount
                "fncg_gld_auto_rdpt_yn": "",
                "pchs_amt_smtl_amt": "1350000",  # Purchase amount total
                "evlu_amt_smtl_amt": "1425000",  # Evaluation amount total
                "evlu_pfls_smtl_amt": "75000",  # Evaluation P/L total
                "tot_stln_slng_chgs": "0",
                "bfdy_tot_asst_evlu_amt": "11350000",
                "asst_icdc_amt": "75000",  # Asset increase/decrease
                "asst_icdc_erng_rt": "0.66"  # Asset earning rate
            }
        ]
    }


def mock_inquire_current_price_success(
    stock_code: str = "005930",
    stock_name: str = "삼성전자",
    current_price: int = 75000,
    opening_price: int = 74500,
    high_price: int = 76000,
    low_price: int = 74000,
    prev_close: int = 73000,
) -> Dict[str, Any]:
    """
    Mock response for inquire_current_price API.

    Args:
        stock_code: 6-digit stock code
        stock_name: Stock name in Korean
        current_price: Current stock price
        opening_price: Opening price
        high_price: Day's high price
        low_price: Day's low price
        prev_close: Previous day's closing price
    """
    price_change = current_price - prev_close
    change_rate = round((price_change / prev_close) * 100, 2)
    sign = "2" if price_change > 0 else "5" if price_change < 0 else "3"

    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": {
            "stck_shrn_iscd": stock_code,
            "stck_prpr": str(current_price),  # Current price
            "prdy_vrss": str(price_change),  # Price change from previous day
            "prdy_vrss_sign": sign,  # 1:상한, 2:상승, 3:보합, 4:하한, 5:하락
            "prdy_ctrt": str(change_rate),  # Change rate
            "stck_oprc": str(opening_price),  # Opening price
            "stck_hgpr": str(high_price),  # High price
            "stck_lwpr": str(low_price),  # Low price
            "stck_mxpr": str(int(prev_close * 1.3)),  # Max price (30% upper limit)
            "stck_llam": str(int(prev_close * 0.7)),  # Lower limit (30% lower limit)
            "stck_sdpr": str(prev_close),  # Previous closing price
            "wghn_avrg_stck_pric": str(current_price),  # Weighted average price
            "hts_frgn_ehrt": "52.00",  # Foreign ownership ratio
            "frgn_ntby_qty": "100000",  # Foreign net buy quantity
            "pgtr_ntby_qty": "50000",  # Program net buy quantity
            "pvt_scnd_dmrs_prc": "0",
            "dmrs_val": "0",
            "cpfn": "000000000001",
            "rstc_wmrk_val": "0",
            "hts_deal_qty_unit_val": "1",
            "lstn_stcn": "5969782550",  # Listed stock count
            "stck_fcam": "0",
            "stck_sspr": str(prev_close),
            "aspr_unit": "100",
            "hts_kprice_info": str(current_price),
            "stck_prdy_clpr": str(prev_close),
            "acml_vol": "15000000",  # Accumulated volume
            "acml_tr_pbmn": "1125000000000",  # Accumulated trading amount
            "seln_cntg_qty": "800000",
            "shnu_cntg_qty": "900000",
            "ntby_cntg_qty": "100000",
            "cttr": "0.50",  # Turnover ratio
            "seln_cntg_smtn": "60000000000",
            "shnu_cntg_smtn": "67500000000",
            "ccld_dvsn": "1",
            "shnu_rate": "52.94",
            "prdy_vol_vrss_acml_vol_rate": "105.50",
            "oprc_hour": "090000",
            "oprc_vrss_prpr_sign": sign,
            "oprc_vrss_prpr": str(current_price - opening_price),
            "hgpr_hour": "133000",
            "hgpr_vrss_prpr_sign": "5",
            "hgpr_vrss_prpr": str(high_price - current_price),
            "lwpr_hour": "093000",
            "lwpr_vrss_prpr_sign": "2",
            "lwpr_vrss_prpr": str(current_price - low_price),
            "bsop_date": datetime.now().strftime("%Y%m%d"),
            "new_mkop_cls_code": "1",
            "trht_yn": "N",
            "askp_rsqn1": "75100",
            "bskp_rsqn1": "74900"
        }
    }


def mock_inquire_daily_price_success(
    stock_code: str = "005930",
    days: int = 5
) -> Dict[str, Any]:
    """
    Mock response for inquire_daily_price API with historical data.

    Args:
        stock_code: 6-digit stock code
        days: Number of days of historical data
    """
    from datetime import timedelta
    base_date = datetime.now()
    base_price = 75000

    output = []
    for i in range(days):
        day_offset = days - i - 1
        date = base_date - timedelta(days=day_offset)
        date_str = date.strftime("%Y%m%d")

        # Simulate price variation
        price_var = (i - days // 2) * 1000
        close_price = base_price + price_var
        open_price = close_price - 500 + (i % 3) * 300
        high_price = max(open_price, close_price) + 500
        low_price = min(open_price, close_price) - 500

        output.append({
            "stck_bsop_date": date_str,
            "stck_clpr": str(close_price),  # Closing price
            "stck_oprc": str(open_price),  # Opening price
            "stck_hgpr": str(high_price),  # High price
            "stck_lwpr": str(low_price),  # Low price
            "acml_vol": str(10000000 + i * 1000000),  # Volume
            "acml_tr_pbmn": str((close_price * (10000000 + i * 1000000)) // 1000),
            "flng_cls_code": "00",
            "prtt_rate": "0.00",
            "mod_yn": "N",
            "prdy_vrss_sign": "2" if i % 2 == 0 else "5",
            "prdy_vrss": str(abs(price_var)),
            "revl_issu_reas": ""
        })

    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": output
    }


def mock_cash_order_success(
    order_no: str = "0000012345",
    stock_code: str = "005930",
    order_qty: int = 10,
    order_price: int = 75000,
    order_time: str = "093015"
) -> Dict[str, Any]:
    """
    Mock successful order response.

    Args:
        order_no: Order number
        stock_code: 6-digit stock code
        order_qty: Order quantity
        order_price: Order price
        order_time: Order time (HHMMSS format)
    """
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": {
            "KRX_FWDG_ORD_ORGNO": "91252",
            "ODNO": order_no,  # Order number
            "ORD_TMD": order_time,  # Order time
        }
    }


def mock_balance_sheet_success(stock_code: str = "005930") -> Dict[str, Any]:
    """
    Mock response for balance sheet API (Samsung Electronics example).

    Args:
        stock_code: 6-digit stock code
    """
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": [
            {
                "stac_yymm": "202312",  # Statement year-month
                "gp_cd": "001",
                "gp_nm": "유동자산",  # Current assets
                "acct_cd": "A001",
                "acct_nm": "현금및현금성자산",
                "bfefr_amont": "65123000000000",  # Amount
                "thstrm_amont": "69456000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "001",
                "gp_nm": "유동자산",
                "acct_cd": "A002",
                "acct_nm": "단기금융상품",
                "bfefr_amont": "85234000000000",
                "thstrm_amont": "92145000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "002",
                "gp_nm": "비유동자산",  # Non-current assets
                "acct_cd": "A010",
                "acct_nm": "유형자산",
                "bfefr_amont": "185234000000000",
                "thstrm_amont": "198456000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "003",
                "gp_nm": "자산총계",  # Total assets
                "acct_cd": "A999",
                "acct_nm": "자산총계",
                "bfefr_amont": "378456000000000",
                "thstrm_amont": "399234000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "004",
                "gp_nm": "부채",  # Liabilities
                "acct_cd": "L001",
                "acct_nm": "유동부채",
                "bfefr_amont": "85234000000000",
                "thstrm_amont": "89456000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "005",
                "gp_nm": "자본",  # Equity
                "acct_cd": "E001",
                "acct_nm": "자본총계",
                "bfefr_amont": "293222000000000",
                "thstrm_amont": "309778000000000"
            }
        ]
    }


def mock_income_statement_success(stock_code: str = "005930") -> Dict[str, Any]:
    """
    Mock response for income statement API.

    Args:
        stock_code: 6-digit stock code
    """
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": [
            {
                "stac_yymm": "202312",
                "gp_cd": "001",
                "gp_nm": "매출액",  # Revenue
                "acct_cd": "I001",
                "acct_nm": "매출액",
                "bfefr_amont": "302231000000000",
                "thstrm_amont": "258940000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "002",
                "gp_nm": "매출원가",  # Cost of sales
                "acct_cd": "I002",
                "acct_nm": "매출원가",
                "bfefr_amont": "185456000000000",
                "thstrm_amont": "169234000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "003",
                "gp_nm": "매출총이익",  # Gross profit
                "acct_cd": "I003",
                "acct_nm": "매출총이익",
                "bfefr_amont": "116775000000000",
                "thstrm_amont": "89706000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "004",
                "gp_nm": "영업이익",  # Operating income
                "acct_cd": "I010",
                "acct_nm": "영업이익",
                "bfefr_amont": "42186000000000",
                "thstrm_amont": "6548000000000"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "005",
                "gp_nm": "당기순이익",  # Net income
                "acct_cd": "I020",
                "acct_nm": "당기순이익",
                "bfefr_amont": "55683000000000",
                "thstrm_amont": "15133000000000"
            }
        ]
    }


def mock_financial_ratio_success(stock_code: str = "005930") -> Dict[str, Any]:
    """
    Mock response for financial ratio API.

    Args:
        stock_code: 6-digit stock code
    """
    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output": [
            {
                "stac_yymm": "202312",
                "gp_cd": "001",
                "gp_nm": "수익성지표",  # Profitability ratios
                "acct_cd": "R001",
                "acct_nm": "ROE",
                "bfefr_amont": "19.00",
                "thstrm_amont": "4.89"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "001",
                "gp_nm": "수익성지표",
                "acct_cd": "R002",
                "acct_nm": "ROA",
                "bfefr_amont": "14.71",
                "thstrm_amont": "3.79"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "002",
                "gp_nm": "안정성지표",  # Stability ratios
                "acct_cd": "R010",
                "acct_nm": "부채비율",  # Debt ratio
                "bfefr_amont": "29.05",
                "thstrm_amont": "28.88"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "002",
                "gp_nm": "안정성지표",
                "acct_cd": "R011",
                "acct_nm": "유동비율",  # Current ratio
                "bfefr_amont": "235.67",
                "thstrm_amont": "240.12"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "003",
                "gp_nm": "성장성지표",  # Growth ratios
                "acct_cd": "R020",
                "acct_nm": "매출액증가율",
                "bfefr_amont": "8.32",
                "thstrm_amont": "-14.32"
            },
            {
                "stac_yymm": "202312",
                "gp_cd": "004",
                "gp_nm": "활동성지표",  # Activity ratios
                "acct_cd": "R030",
                "acct_nm": "총자산회전율",
                "bfefr_amont": "0.80",
                "thstrm_amont": "0.65"
            }
        ]
    }


# ============================================================================
# Error Response Fixtures
# ============================================================================


def mock_error_response(
    rt_cd: str = "-1",
    msg_cd: str = "EGW00123",
    msg1: str = "기타오류"
) -> Dict[str, Any]:
    """
    Mock generic error response.

    Args:
        rt_cd: Return code (non-zero for errors)
        msg_cd: Error message code
        msg1: Error message text
    """
    return {
        "rt_cd": rt_cd,
        "msg_cd": msg_cd,
        "msg1": msg1,
        "output": {}
    }


def mock_auth_error() -> Dict[str, Any]:
    """Mock authentication error response."""
    return {
        "rt_cd": "-1",
        "msg_cd": "EGW00201",
        "msg1": "인증 오류",
        "output": {}
    }


def mock_invalid_stock_code_error() -> Dict[str, Any]:
    """Mock invalid stock code error response."""
    return {
        "rt_cd": "1",
        "msg_cd": "MCA00001",
        "msg1": "종목코드 오류",
        "output": {}
    }


def mock_insufficient_balance_error() -> Dict[str, Any]:
    """Mock insufficient balance error for order."""
    return {
        "rt_cd": "1",
        "msg_cd": "MCA00111",
        "msg1": "주문가능금액을 초과하였습니다.",
        "output": {}
    }


def mock_market_closed_error() -> Dict[str, Any]:
    """Mock market closed error."""
    return {
        "rt_cd": "1",
        "msg_cd": "MCA00222",
        "msg1": "장운영시간이 아닙니다.",
        "output": {}
    }


def mock_rate_limit_error() -> Dict[str, Any]:
    """Mock API rate limit error."""
    return {
        "rt_cd": "-1",
        "msg_cd": "EGW00133",
        "msg1": "API 호출 한도를 초과하였습니다.",
        "output": {}
    }


# ============================================================================
# Factory Functions
# ============================================================================


def create_balance_position(
    stock_code: str,
    stock_name: str,
    quantity: int,
    avg_price: int,
    current_price: int
) -> Dict[str, Any]:
    """
    Create a single balance position entry.

    Args:
        stock_code: 6-digit stock code
        stock_name: Stock name in Korean
        quantity: Holding quantity
        avg_price: Average purchase price
        current_price: Current market price
    """
    purchase_amt = quantity * avg_price
    eval_amt = quantity * current_price
    profit_loss = eval_amt - purchase_amt
    profit_loss_rate = round((profit_loss / purchase_amt) * 100, 2) if purchase_amt > 0 else 0.0
    price_change = current_price - avg_price

    return {
        "pdno": stock_code,
        "prdt_name": stock_name,
        "trad_dvsn_name": "현금",
        "bfdy_buy_qty": str(quantity),
        "bfdy_sll_qty": "0",
        "thdt_buyqty": "0",
        "thdt_sll_qty": "0",
        "hldg_qty": str(quantity),
        "ord_psbl_qty": str(quantity),
        "pchs_avg_pric": f"{avg_price:.2f}",
        "pchs_amt": str(purchase_amt),
        "prpr": str(current_price),
        "evlu_amt": str(eval_amt),
        "evlu_pfls_amt": str(profit_loss),
        "evlu_pfls_rt": f"{profit_loss_rate:.2f}",
        "evlu_erng_rt": f"{profit_loss_rate:.2f}",
        "loan_dt": "",
        "loan_amt": "0",
        "stln_slng_chgs": "0",
        "expd_dt": "",
        "fltt_rt": "0.00",
        "bfdy_cprs_icdc": str(price_change),
        "item_mgna_rt_name": "20%",
        "grta_rt_name": "",
        "sbst_pric": str(current_price),
        "stck_loan_unpr": "0.00"
    }


def create_custom_balance(
    positions: List[Dict[str, Any]],
    cash_balance: int = 10000000
) -> Dict[str, Any]:
    """
    Create a custom balance response with specified positions.

    Args:
        positions: List of position dictionaries from create_balance_position()
        cash_balance: Available cash balance
    """
    total_purchase = sum(int(p["pchs_amt"]) for p in positions)
    total_eval = sum(int(p["evlu_amt"]) for p in positions)
    total_pl = total_eval - total_purchase
    total_assets = cash_balance + total_eval

    return {
        "rt_cd": "0",
        "msg_cd": "MCA00000",
        "msg1": "정상처리 되었습니다.",
        "output1": positions,
        "output2": [
            {
                "dnca_tot_amt": str(cash_balance),
                "nxdy_excc_amt": str(cash_balance - total_purchase),
                "prvs_rcdl_excc_amt": str(cash_balance - total_purchase),
                "cma_evlu_amt": "0",
                "bfdy_buy_amt": "0",
                "thdt_buy_amt": "0",
                "nxdy_auto_rdpt_amt": "0",
                "bfdy_sll_amt": "0",
                "thdt_sll_amt": "0",
                "d2_auto_rdpt_amt": "0",
                "bfdy_tlex_amt": "0",
                "thdt_tlex_amt": "0",
                "tot_loan_amt": "0",
                "scts_evlu_amt": str(total_eval),
                "tot_evlu_amt": str(total_assets),
                "nass_amt": str(total_assets),
                "fncg_gld_auto_rdpt_yn": "",
                "pchs_amt_smtl_amt": str(total_purchase),
                "evlu_amt_smtl_amt": str(total_eval),
                "evlu_pfls_smtl_amt": str(total_pl),
                "tot_stln_slng_chgs": "0",
                "bfdy_tot_asst_evlu_amt": str(total_assets - total_pl),
                "asst_icdc_amt": str(total_pl),
                "asst_icdc_erng_rt": f"{(total_pl / (total_assets - total_pl) * 100):.2f}" if total_assets != total_pl else "0.00"
            }
        ]
    }


# ============================================================================
# Additional Test Stocks
# ============================================================================


# Common test stocks with realistic data
TEST_STOCKS = {
    "005930": {"name": "삼성전자", "price": 75000},
    "000660": {"name": "SK하이닉스", "price": 135000},
    "035420": {"name": "NAVER", "price": 210000},
    "005380": {"name": "현대차", "price": 185000},
    "051910": {"name": "LG화학", "price": 420000},
    "006400": {"name": "삼성SDI", "price": 450000},
    "035720": {"name": "카카오", "price": 48000},
    "068270": {"name": "셀트리온", "price": 165000},
    "207940": {"name": "삼성바이오로직스", "price": 850000},
    "373220": {"name": "LG에너지솔루션", "price": 380000},
}


def get_test_stock_info(stock_code: str) -> Optional[Dict[str, Any]]:
    """
    Get test stock information by code.

    Args:
        stock_code: 6-digit stock code

    Returns:
        Dictionary with name and price, or None if not found
    """
    return TEST_STOCKS.get(stock_code)
