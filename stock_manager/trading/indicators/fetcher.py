"""Technical data fetcher: assembles MarketSnapshot from KIS APIs.

Calls multiple KIS API endpoints and combines fundamental, price, and
technical data into a single immutable MarketSnapshot for persona evaluation.

API endpoints used:
    - inquire_current_price   (basic.py)  -- price, volume, 52w high/low
    - get_financial_ratio     (info.py)   -- P/E, P/B, ROE, EPS, etc.
    - get_balance_sheet       (info.py)   -- assets, liabilities, equity items
    - inquire_period_price    (basic.py)  -- OHLCV history for technicals
    - get_income_statement    (info.py)   -- revenue, margins
    - get_growth_ratio        (info.py)   -- YoY growth rates
    - get_profit_ratio        (info.py)   -- profitability ratios
    - get_stability_ratio     (info.py)   -- debt/equity, current ratio
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from stock_manager.adapters.broker.kis.exceptions import KISAPIError
from stock_manager.trading.personas.models import MarketSnapshot
from stock_manager.pipeline.indicators import (
    compute_snapshot_ohlcv,
    parse_kis_ohlcv,
)
from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import (
    inquire_current_price,
    inquire_period_price,
)
from stock_manager.adapters.broker.kis.apis.domestic_stock.info import (
    get_balance_sheet,
    get_financial_ratio,
    get_growth_ratio,
    get_income_statement,
    get_profit_ratio,
    get_stability_ratio,
)
from stock_manager.trading.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
_DEFAULT_FETCHER_RATE_LIMIT_PER_SEC = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_decimal(value: Any, default: str = "0") -> Decimal:
    """Convert API value to Decimal, returning default on failure."""
    if value is None:
        return Decimal(default)
    try:
        s = str(value).strip().replace(",", "")
        if not s or s == "-":
            return Decimal(default)
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert API value to float, returning default on failure."""
    if value is None:
        return default
    try:
        s = str(value).strip().replace(",", "")
        if not s or s == "-":
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert API value to int, returning default on failure."""
    if value is None:
        return default
    try:
        s = str(value).strip().replace(",", "")
        if not s or s == "-":
            return default
        return int(float(s))
    except (ValueError, TypeError):
        return default


def _get_output(response: dict[str, Any]) -> dict[str, Any]:
    """Extract 'output' from KIS API response, handling list vs dict."""
    if response.get("rt_cd") != "0":
        return {}
    output = response.get("output", {})
    if isinstance(output, list):
        return output[0] if output else {}
    return output


def _get_output_list(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract 'output' as list from KIS API response."""
    if response.get("rt_cd") != "0":
        return []
    output = response.get("output", [])
    if isinstance(output, dict):
        return [output]
    return output if isinstance(output, list) else []


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


class TechnicalDataFetcher:
    """Assembles a MarketSnapshot by calling KIS REST APIs.

    Args:
        client: KISRestClient instance for making API requests.
    """

    def __init__(
        self,
        client: Any,
        *,
        rate_limiter: RateLimiter | None = None,
        rate_limit_per_sec: int = _DEFAULT_FETCHER_RATE_LIMIT_PER_SEC,
    ) -> None:
        self.client = client
        self._rate_limiter = rate_limiter or RateLimiter(max_requests=max(1, rate_limit_per_sec))
        self._mock_skip_log_once: set[str] = set()

    def _is_mock_mode(self) -> bool:
        config = getattr(self.client, "config", None)
        return bool(getattr(config, "use_mock", False))

    def _is_rate_limit_error(self, error: KISAPIError) -> bool:
        if error.status_code == 429:
            return True
        payload = error.response_data or {}
        msg_cd = str(payload.get("msg_cd", "")).upper()
        msg1 = str(payload.get("msg1", ""))
        return msg_cd == "EGW00201" or "초당 거래건수" in msg1

    def _call_kis_api(
        self,
        api_name: str,
        fn: Callable[..., dict[str, Any]],
        *args: Any,
        skip_in_mock: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if skip_in_mock and self._is_mock_mode():
            if api_name not in self._mock_skip_log_once:
                logger.info("Skipping real-only API %s in mock mode", api_name)
                self._mock_skip_log_once.add(api_name)
            return {}

        self._rate_limiter.acquire()
        try:
            return fn(self.client, *args, **kwargs)
        except KISAPIError as error:
            if self._is_rate_limit_error(error):
                logger.warning("Rate limit exceeded while calling %s; using degraded data", api_name)
            else:
                logger.exception("Failed to call %s", api_name)
            return {}
        except Exception:
            logger.exception("Failed to call %s", api_name)
            return {}

    def fetch_snapshot(self, symbol: str) -> MarketSnapshot:
        """Fetch all data and assemble a MarketSnapshot for the given symbol.

        Makes multiple KIS API calls sequentially:
            1. Current price data
            2. Financial ratios (P/E, P/B, ROE, EPS)
            3. Balance sheet
            4. Period price history (OHLCV for technical indicators)
            5. Income statement
            6. Growth ratios
            7. Profitability ratios
            8. Stability ratios

        Args:
            symbol: 6-digit stock code (e.g., '005930').

        Returns:
            Fully populated MarketSnapshot (frozen dataclass).
        """
        # --- 1. Current price ---
        price_data = self._fetch_current_price(symbol)

        # --- 2. Financial ratios ---
        fin_ratio = self._fetch_financial_ratio(symbol)

        # --- 3. Balance sheet ---
        balance = self._fetch_balance_sheet(symbol)

        # --- 4. OHLCV history + technical indicators ---
        technicals = self._fetch_technicals(symbol)

        # --- 5. Income statement ---
        income = self._fetch_income_statement(symbol)

        # --- 6. Growth ratios ---
        growth = self._fetch_growth_ratio(symbol)

        # --- 7. Profit ratios ---
        profit = self._fetch_profit_ratio(symbol)

        # --- 8. Stability ratios ---
        stability = self._fetch_stability_ratio(symbol)

        # --- 9. Market context ---
        vkospi = self._fetch_vkospi()

        # --- Assemble MarketSnapshot ---
        return MarketSnapshot(
            # Group 1: Price / Quote
            symbol=symbol,
            name=price_data.get("name", ""),
            market="KRX",
            sector=price_data.get("sector", ""),
            timestamp=datetime.now(timezone.utc),
            current_price=_safe_decimal(price_data.get("current_price")),
            open_price=_safe_decimal(price_data.get("open_price")),
            high_price=_safe_decimal(price_data.get("high_price")),
            low_price=_safe_decimal(price_data.get("low_price")),
            prev_close=_safe_decimal(price_data.get("prev_close")),
            volume=_safe_int(price_data.get("volume")),
            avg_volume_20d=technicals.get("avg_volume_20d", 0),
            # Group 2: Valuation
            market_cap=_safe_decimal(fin_ratio.get("market_cap")),
            per=_safe_float(fin_ratio.get("per")),
            pbr=_safe_float(fin_ratio.get("pbr")),
            eps=_safe_decimal(fin_ratio.get("eps")),
            bps=_safe_decimal(fin_ratio.get("bps")),
            dividend_yield=_safe_float(fin_ratio.get("dividend_yield")),
            roe=_safe_float(profit.get("roe")),
            # Group 3: Financial Health
            current_ratio=_safe_float(stability.get("current_ratio")),
            debt_to_equity=_safe_float(stability.get("debt_to_equity")),
            operating_margin=_safe_float(profit.get("operating_margin")),
            net_margin=_safe_float(profit.get("net_margin")),
            free_cash_flow=_safe_decimal(income.get("operating_income", 0)),  # FCF proxy: operating income (KIS API lacks cash flow statement)
            # Group 4: Growth
            revenue_growth_yoy=_safe_float(growth.get("revenue_growth_yoy")),
            earnings_growth_yoy=_safe_float(growth.get("earnings_growth_yoy")),
            revenue_growth_3yr=None,  # Not available from single API call
            earnings_growth_3yr=None,
            # Group 5: Technical (from OHLCV indicators)
            sma_20=technicals.get("sma_20", 0.0),
            sma_50=technicals.get("sma_50", 0.0),
            sma_200=technicals.get("sma_200", 0.0),
            rsi_14=technicals.get("rsi_14", 0.0),
            macd_signal=technicals.get("macd_signal", 0.0),
            bollinger_position=technicals.get("bollinger_position", 0.0),
            adx_14=technicals.get("adx_14", 0.0),
            atr_14=technicals.get("atr_14", 0.0),
            # Group 6: Balance Sheet
            total_assets=_safe_decimal(balance.get("total_assets")),
            total_liabilities=_safe_decimal(balance.get("total_liabilities")),
            current_assets=_safe_decimal(balance.get("current_assets")),
            cash_and_equivalents=_safe_decimal(balance.get("cash_and_equivalents")),
            inventory=_safe_decimal(balance.get("inventory")),
            accounts_receivable=_safe_decimal(balance.get("accounts_receivable")),
            shares_outstanding=_safe_int(balance.get("shares_outstanding")),
            # Group 7: History
            price_52w_high=_safe_decimal(price_data.get("price_52w_high")),
            price_52w_low=_safe_decimal(price_data.get("price_52w_low")),
            years_positive_earnings=_safe_int(fin_ratio.get("years_positive_earnings")),
            years_dividends_paid=_safe_int(fin_ratio.get("years_dividends_paid")),
            # Group 8: Market Context
            vkospi=vkospi,
            kospi_per=self._fetch_kospi_per(),
        )

    # ------------------------------------------------------------------
    # Private fetch methods
    # ------------------------------------------------------------------

    def _fetch_current_price(self, symbol: str) -> dict[str, Any]:
        """Fetch current price data from KIS API."""
        response = self._call_kis_api("inquire_current_price", inquire_current_price, symbol)
        output = _get_output(response)
        if not output:
            return {}
        return {
            "current_price": output.get("stck_prpr"),
            "open_price": output.get("stck_oprc"),
            "high_price": output.get("stck_hgpr"),
            "low_price": output.get("stck_lwpr"),
            "prev_close": output.get("stck_sdpr"),
            "volume": output.get("acml_vol"),
            "price_52w_high": output.get("stck_dryy_hgpr"),
            "price_52w_low": output.get("stck_dryy_lwpr"),
            "name": output.get("hts_kor_isnm", ""),
            "sector": output.get("bstp_kor_isnm", ""),
        }

    def _fetch_financial_ratio(self, symbol: str) -> dict[str, Any]:
        """Fetch financial ratios (P/E, P/B, EPS, etc.)."""
        response = self._call_kis_api(
            "get_financial_ratio",
            get_financial_ratio,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "per": output.get("per"),
            "pbr": output.get("pbr"),
            "eps": output.get("eps"),
            "bps": output.get("bps"),
            "dividend_yield": output.get("dvd_yld"),
            "market_cap": output.get("hts_avls"),
            "years_positive_earnings": 1 if _safe_float(output.get("eps")) > 0 else 0,  # KIS API limitation: only current year EPS available
            "years_dividends_paid": 1 if _safe_float(output.get("dvd_yld")) > 0 else 0,  # KIS API limitation: only current dividend yield available
        }

    def _fetch_balance_sheet(self, symbol: str) -> dict[str, Any]:
        """Fetch balance sheet data."""
        response = self._call_kis_api(
            "get_balance_sheet",
            get_balance_sheet,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "total_assets": output.get("total_aset"),
            "total_liabilities": output.get("total_lblt"),
            "current_assets": output.get("flow_aset"),
            "cash_and_equivalents": output.get("cash_aset"),
            "inventory": output.get("ivtm"),
            "accounts_receivable": output.get("trad_rciv"),
            "shares_outstanding": output.get("lstg_stqt"),
        }

    def _fetch_technicals(self, symbol: str) -> dict[str, Any]:
        """Fetch OHLCV history and compute technical indicators."""
        try:
            end_date = datetime.now(timezone.utc).strftime("%Y%m%d")
            start_date = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y%m%d")

            response = self._call_kis_api(
                "inquire_period_price",
                inquire_period_price,
                symbol,
                period_code="D",
                fid_cond_mrkt_div_code="J",
                fid_input_date_1=start_date,
                fid_input_date_2=end_date,
                fid_org_adj_prc="1",
            )

            output_list = _get_output_list(response)
            if not output_list:
                return {}

            # Also try output2 for continuation data
            output2 = response.get("output2", [])
            if isinstance(output2, list):
                output_list = output_list + output2

            ohlcv = parse_kis_ohlcv(output_list)
            if not ohlcv:
                return {}

            snap = compute_snapshot_ohlcv(symbol, ohlcv)

            # Compute actual 20-day average volume from OHLCV
            if len(ohlcv) >= 20:
                recent_20 = ohlcv[-20:]
                avg_vol = sum(bar.volume for bar in recent_20) // 20
            else:
                avg_vol = sum(bar.volume for bar in ohlcv) // max(len(ohlcv), 1)

            return {
                "sma_20": snap.sma20 or 0.0,
                "sma_50": snap.sma60 or 0.0,  # Use SMA-60 as proxy for SMA-50
                "sma_200": snap.sma200 or 0.0,
                "rsi_14": snap.rsi14 or 0.0,
                "macd_signal": snap.macd_signal or 0.0,
                "bollinger_position": snap.bb_pct_b or 0.0,
                "adx_14": snap.adx14 or 0.0,
                "atr_14": snap.atr14 or 0.0,
                "avg_volume_20d": avg_vol,
            }
        except Exception:
            logger.exception("Failed to fetch technicals for %s", symbol)
            return {}

    def _fetch_vkospi(self) -> float | None:
        """Fetch VKOSPI (Korean VIX) as market stress indicator."""
        response = self._call_kis_api("inquire_current_price_vkospi", inquire_current_price, "580003")
        output = _get_output(response)
        value = _safe_float(output.get("stck_prpr"), default=0.0)
        return value if value > 0 else None

    def _fetch_kospi_per(self) -> float:
        """Fetch KOSPI market average P/E ratio.

        Returns configurable default as KIS API does not expose market-wide P/E directly.
        """
        return 12.0  # KOSPI 10-year average P/E

    def _fetch_income_statement(self, symbol: str) -> dict[str, Any]:
        """Fetch income statement data."""
        response = self._call_kis_api(
            "get_income_statement",
            get_income_statement,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "revenue": output.get("sale_account"),
            "operating_income": output.get("bsop_prti"),
            "net_income": output.get("thtr_ntin"),
        }

    def _fetch_growth_ratio(self, symbol: str) -> dict[str, Any]:
        """Fetch growth ratios."""
        response = self._call_kis_api(
            "get_growth_ratio",
            get_growth_ratio,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "revenue_growth_yoy": output.get("sale_gror"),
            "earnings_growth_yoy": output.get("thtr_ntin_gror"),
        }

    def _fetch_profit_ratio(self, symbol: str) -> dict[str, Any]:
        """Fetch profitability ratios."""
        response = self._call_kis_api(
            "get_profit_ratio",
            get_profit_ratio,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "roe": output.get("roe_val"),
            "operating_margin": output.get("bsop_prfi_inrt"),
            "net_margin": output.get("thtr_ntin_inrt"),
        }

    def _fetch_stability_ratio(self, symbol: str) -> dict[str, Any]:
        """Fetch stability ratios."""
        response = self._call_kis_api(
            "get_stability_ratio",
            get_stability_ratio,
            fid_input_iscd=symbol,
            fid_cond_mrkt_div_code="J",
            skip_in_mock=True,
        )
        output = _get_output(response)
        if not output:
            return {}
        return {
            "debt_to_equity": output.get("lblt_rate"),
            "current_ratio": output.get("flow_rate"),
        }
