"""Tests for domestic stock orders API functions.

Following Kent Beck TDD methodology:
- RED: Write failing test that documents expected behavior
- GREEN: Make tests pass with minimal implementation
- REFACTOR: Improve code while keeping tests green
"""

import pytest
from unittest.mock import MagicMock

from stock_manager.adapters.broker.kis.apis.domestic_stock import orders


# =============================================================================
# get_tr_id_cash_order Tests
# =============================================================================


class TestGetTrIdCashOrder:
    """Tests for get_tr_id_cash_order helper function."""

    def test_buy_real_trading(self):
        result = orders.get_tr_id_cash_order("buy", is_paper_trading=False)
        assert result == "TTTC0012U"

    def test_sell_real_trading(self):
        result = orders.get_tr_id_cash_order("sell", is_paper_trading=False)
        assert result == "TTTC0011U"

    def test_buy_paper_trading(self):
        result = orders.get_tr_id_cash_order("buy", is_paper_trading=True)
        assert result == "VTTC0012U"

    def test_sell_paper_trading(self):
        result = orders.get_tr_id_cash_order("sell", is_paper_trading=True)
        assert result == "VTTC0011U"


# =============================================================================
# get_tr_id_credit_order Tests
# =============================================================================


class TestGetTrIdCreditOrder:
    """Tests for get_tr_id_credit_order helper function."""

    def test_buy_credit_order(self):
        result = orders.get_tr_id_credit_order("buy")
        assert result == "TTTC0052U"

    def test_sell_credit_order(self):
        result = orders.get_tr_id_credit_order("sell")
        assert result == "TTTC0051U"


# =============================================================================
# cash_order Tests
# =============================================================================


class TestCashOrder:
    """Tests for cash_order function."""

    def test_cash_order_buy_defaults(self):
        result = orders.cash_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="buy",
            is_paper_trading=False,
        )
        assert result["tr_id"] == "TTTC0012U"
        assert result["params"]["CANO"] == "12345678"
        assert result["params"]["PDNO"] == "005930"
        assert result["params"]["ORD_QTY"] == "10"

    def test_cash_order_sell(self):
        result = orders.cash_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="sell",
            is_paper_trading=False,
        )
        assert result["tr_id"] == "TTTC0011U"

    def test_cash_order_with_price(self):
        result = orders.cash_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="00", ord_qty=10, ord_unsl="01", order_type="buy",
            ord_prc=80000, is_paper_trading=False,
        )
        assert result["params"]["ORD_PRC"] == "80000"

    def test_cash_order_paper_trading(self):
        result = orders.cash_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="buy",
            is_paper_trading=True,
        )
        assert result["tr_id"] == "VTTC0012U"

    def test_cash_order_custom_tr_id(self):
        result = orders.cash_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="buy",
            tr_id="CUSTOM_TR_ID", is_paper_trading=False,
        )
        assert result["tr_id"] == "CUSTOM_TR_ID"


# =============================================================================
# credit_order Tests
# =============================================================================


class TestCreditOrder:
    """Tests for credit_order function."""

    def test_credit_order_buy(self):
        result = orders.credit_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="buy",
        )
        assert result["tr_id"] == "TTTC0052U"

    def test_credit_order_sell(self):
        result = orders.credit_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="sell",
        )
        assert result["tr_id"] == "TTTC0051U"

    def test_credit_order_with_price(self):
        result = orders.credit_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="00", ord_qty=10, ord_unsl="01", order_type="buy",
            ord_prc=80000,
        )
        assert result["params"]["ORD_PRC"] == "80000"

    def test_credit_order_custom_tr_id(self):
        result = orders.credit_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01", order_type="buy",
            tr_id="CUSTOM_TR_ID",
        )
        assert result["tr_id"] == "CUSTOM_TR_ID"


# =============================================================================
# order_cancel Tests
# =============================================================================


class TestOrderCancel:
    """Tests for order_cancel function."""

    def test_order_cancel_real_trading(self):
        result = orders.order_cancel(
            cano="12345678", acnt_prdt_cd="01", orgn_odno="0000012345",
            orgn_ord_dv="00", is_paper_trading=False,
        )
        assert result["tr_id"] == "TTTC0013U"
        assert result["params"]["ORGN_ODNO"] == "0000012345"

    def test_order_cancel_paper_trading(self):
        result = orders.order_cancel(
            cano="12345678", acnt_prdt_cd="01", orgn_odno="0000012345",
            orgn_ord_dv="00", is_paper_trading=True,
        )
        assert result["tr_id"] == "VTTC0013U"

    def test_order_cancel_custom_tr_id(self):
        result = orders.order_cancel(
            cano="12345678", acnt_prdt_cd="01", orgn_odno="0000012345",
            orgn_ord_dv="00", tr_id="CUSTOM_TR_ID",
        )
        assert result["tr_id"] == "CUSTOM_TR_ID"


# =============================================================================
# inquire_psbl_rvsecncl Tests
# =============================================================================


class TestInquirePsblRvsecncl:
    """Tests for inquire_psbl_rvsecncl function."""

    def test_inquire_psbl_rvsecncl_defaults(self):
        result = orders.inquire_psbl_rvsecncl(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC0084R"
        assert result["params"]["CANO"] == "12345678"

    def test_inquire_psbl_rvsecncl_custom_tr_id(self):
        result = orders.inquire_psbl_rvsecncl(
            cano="12345678", acnt_prdt_cd="01", tr_id="CUSTOM_TR_ID",
        )
        assert result["tr_id"] == "CUSTOM_TR_ID"


# =============================================================================
# inquire_daily_ccld Tests
# =============================================================================


class TestInquireDailyCcld:
    """Tests for inquire_daily_ccld function."""

    def test_inquire_daily_ccld_recent_real(self):
        result = orders.inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", ord_dt="20240115",
            is_paper_trading=False, is_old_period=False,
        )
        assert result["tr_id"] == "TTTC0081R"
        assert result["params"]["ORD_DT"] == "20240115"

    def test_inquire_daily_ccld_recent_paper(self):
        result = orders.inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", ord_dt="20240115",
            is_paper_trading=True, is_old_period=False,
        )
        assert result["tr_id"] == "VTTC0081R"

    def test_inquire_daily_ccld_old_real(self):
        result = orders.inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", ord_dt="20231001",
            is_paper_trading=False, is_old_period=True,
        )
        assert result["tr_id"] == "CTSC9215R"

    def test_inquire_daily_ccld_old_paper(self):
        result = orders.inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", ord_dt="20231001",
            is_paper_trading=True, is_old_period=True,
        )
        assert result["tr_id"] == "VTSC9215R"


# =============================================================================
# inquire_balance Tests
# =============================================================================


class TestInquireBalance:
    """Tests for inquire_balance function."""

    def test_inquire_balance_real_trading(self):
        result = orders.inquire_balance(
            cano="12345678", acnt_prdt_cd="01", is_paper_trading=False,
        )
        assert result["tr_id"] == "TTTC8434R"

    def test_inquire_balance_paper_trading(self):
        result = orders.inquire_balance(
            cano="12345678", acnt_prdt_cd="01", is_paper_trading=True,
        )
        assert result["tr_id"] == "VTTC8434R"


# =============================================================================
# inquire_balance_rlz_pl Tests
# =============================================================================


class TestInquireBalanceRlzPl:
    """Tests for inquire_balance_rlz_pl function."""

    def test_inquire_balance_rlz_pl_defaults(self):
        result = orders.inquire_balance_rlz_pl(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC8494R"

    def test_inquire_balance_rlz_pl_custom_tr_id(self):
        result = orders.inquire_balance_rlz_pl(
            cano="12345678", acnt_prdt_cd="01", tr_id="CUSTOM_TR_ID",
        )
        assert result["tr_id"] == "CUSTOM_TR_ID"


# =============================================================================
# inquire_psbl_order Tests
# =============================================================================


class TestInquirePsblOrder:
    """Tests for inquire_psbl_order function."""

    def test_inquire_psbl_order_real_trading(self):
        result = orders.inquire_psbl_order(
            cano="12345678", acnt_prdt_cd="01", is_paper_trading=False,
        )
        assert result["tr_id"] == "TTTC8908R"

    def test_inquire_psbl_order_paper_trading(self):
        result = orders.inquire_psbl_order(
            cano="12345678", acnt_prdt_cd="01", is_paper_trading=True,
        )
        assert result["tr_id"] == "VTTC8908R"

    def test_inquire_psbl_order_with_pdno(self):
        result = orders.inquire_psbl_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
        )
        assert result["params"]["PDNO"] == "005930"


# =============================================================================
# inquire_psbl_sell Tests
# =============================================================================


class TestInquirePsblSell:
    """Tests for inquire_psbl_sell function."""

    def test_inquire_psbl_sell_defaults(self):
        result = orders.inquire_psbl_sell(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
        )
        assert result["tr_id"] == "TTTC8408R"
        assert result["params"]["PDNO"] == "005930"


# =============================================================================
# inquire_credit_psamount Tests
# =============================================================================


class TestInquireCreditPsamount:
    """Tests for inquire_credit_psamount function."""

    def test_inquire_credit_psamount_defaults(self):
        result = orders.inquire_credit_psamount(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC8909R"

    def test_inquire_credit_psamount_with_pdno(self):
        result = orders.inquire_credit_psamount(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
        )
        assert result["params"]["PDNO"] == "005930"


# =============================================================================
# order_resv Tests
# =============================================================================


class TestOrderResv:
    """Tests for order_resv function."""

    def test_order_resv_defaults(self):
        result = orders.order_resv(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="01", ord_qty=10, ord_unsl="01",
        )
        assert result["tr_id"] == "CTSC0008U"
        assert result["params"]["ORD_QTY"] == "10"

    def test_order_resv_with_price(self):
        result = orders.order_resv(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
            ord_dv="00", ord_qty=10, ord_unsl="01", ord_prc=80000,
        )
        assert result["params"]["ORD_PRC"] == "80000"


# =============================================================================
# order_resv_rvsecncl Tests
# =============================================================================


class TestOrderResvRvsecncl:
    """Tests for order_resv_rvsecncl function."""

    def test_order_resv_rvsecncl_cancel(self):
        result = orders.order_resv_rvsecncl(
            cano="12345678", acnt_prdt_cd="01", orgn_odno="0000012345",
            rvse_cncl_dv="cancel",
        )
        assert result["tr_id"] == "CTSC0009U"

    def test_order_resv_rvsecncl_revise(self):
        result = orders.order_resv_rvsecncl(
            cano="12345678", acnt_prdt_cd="01", orgn_odno="0000012345",
            rvse_cncl_dv="revise",
        )
        assert result["tr_id"] == "CTSC0013U"


# =============================================================================
# order_resv_ccnl Tests
# =============================================================================


class TestOrderResvCcnl:
    """Tests for order_resv_ccnl function."""

    def test_order_resv_ccnl_defaults(self):
        result = orders.order_resv_ccnl(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "CTSC0004R"


# =============================================================================
# Pension API Tests
# =============================================================================


class TestPensionAPIs:
    """Tests for pension-related API functions."""

    def test_pension_inquire_present_balance(self):
        result = orders.pension_inquire_present_balance(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC2202R"

    def test_pension_inquire_daily_ccld_krx_only(self):
        result = orders.pension_inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", use_nxt=False,
        )
        assert result["tr_id"] == "TTTC2201R"

    def test_pension_inquire_daily_ccld_nxt_sor(self):
        result = orders.pension_inquire_daily_ccld(
            cano="12345678", acnt_prdt_cd="01", use_nxt=True,
        )
        assert result["tr_id"] == "TTTC2210R"

    def test_pension_inquire_psbl_order(self):
        result = orders.pension_inquire_psbl_order(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC0503R"

    def test_pension_inquire_psbl_order_with_pdno(self):
        result = orders.pension_inquire_psbl_order(
            cano="12345678", acnt_prdt_cd="01", pdno="005930",
        )
        assert result["params"]["PDNO"] == "005930"

    def test_pension_inquire_deposit(self):
        result = orders.pension_inquire_deposit(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC0506R"

    def test_pension_inquire_balance(self):
        result = orders.pension_inquire_balance(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC2208R"


# =============================================================================
# Other Inquiry API Tests
# =============================================================================


class TestOtherInquiryAPIs:
    """Tests for other inquiry API functions."""

    def test_inquire_account_balance(self):
        result = orders.inquire_account_balance(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "CTRP6548R"

    def test_inquire_period_profit(self):
        result = orders.inquire_period_profit(
            cano="12345678", acnt_prdt_cd="01",
            str_dt="20240101", end_dt="20240131",
        )
        assert result["tr_id"] == "TTTC8708R"
        assert result["params"]["STR_DT"] == "20240101"
        assert result["params"]["END_DT"] == "20240131"

    def test_inquire_period_trade_profit(self):
        result = orders.inquire_period_trade_profit(
            cano="12345678", acnt_prdt_cd="01",
            str_dt="20240101", end_dt="20240131",
        )
        assert result["tr_id"] == "TTTC8715R"

    def test_intgr_margin(self):
        result = orders.intgr_margin(
            cano="12345678", acnt_prdt_cd="01",
        )
        assert result["tr_id"] == "TTTC0869R"

    def test_period_rights(self):
        result = orders.period_rights(
            cano="12345678", acnt_prdt_cd="01",
            str_dt="20240101", end_dt="20240131",
        )
        assert result["tr_id"] == "CTRGA011R"
