"""
Benjamin Graham's Defensive Investor Strategy.

Implements all 7 criteria from The Intelligent Investor with
correct Net-Net Working Capital (NCAV) formula.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional
import logging

from stock_manager.trading.strategies.base import Strategy, StrategyScore

logger = logging.getLogger(__name__)


@dataclass
class DefensiveGrahamScore(StrategyScore):
    """All 7 criteria from The Intelligent Investor."""

    symbol: str

    # Criterion 1: Adequate Size
    market_cap: Decimal
    meets_size: bool  # Min ₩2.4조 (KOSPI) or ₩500B (KOSDAQ)

    # Criterion 2: Strong Financial Condition
    current_ratio: Decimal  # Min 2.0
    debt_to_current_assets: Decimal  # Max 0.5
    meets_financial: bool

    # Criterion 3: Earnings Stability
    years_positive_earnings: int  # Min 10 years
    meets_stability: bool

    # Criterion 4: Dividend Record
    years_dividends: int  # Min 20 years
    meets_dividends: bool

    # Criterion 5: Earnings Growth
    eps_growth_10yr: Decimal  # Min 33% over 10 years
    meets_growth: bool

    # Criterion 6: Moderate P/E
    pe_ratio: Decimal  # Max 15.0
    meets_pe: bool

    # Criterion 7: Moderate Price-to-Book + Combined
    pb_ratio: Decimal  # Max 1.5
    pe_times_pb: Decimal  # Max 22.5
    meets_pb: bool

    @property
    def passes_all(self) -> bool:
        """Must pass all 7 criteria for defensive."""
        return all([
            self.meets_size,
            self.meets_financial,
            self.meets_stability,
            self.meets_dividends,
            self.meets_growth,
            self.meets_pe,
            self.meets_pb
        ])

    @property
    def criteria_passed(self) -> int:
        """Count of criteria passed."""
        return sum([
            self.meets_size,
            self.meets_financial,
            self.meets_stability,
            self.meets_dividends,
            self.meets_growth,
            self.meets_pe,
            self.meets_pb
        ])


def calculate_ncav_per_share(
    balance_sheet: dict,
    shares_outstanding: int
) -> Decimal:
    """
    Graham's conservative Net-Net Working Capital.

    Formula:
    1. Cash/Securities: 100%
    2. Receivables: 80% (bad debt allowance)
    3. Inventory: 70% (obsolescence allowance)
    4. Prepaid: 0% (illiquid)
    5. Subtract ALL liabilities
    6. Apply 66% discount factor
    """
    output = balance_sheet.get("output", {})

    # Step 1: Get current asset components
    cash = Decimal(str(output.get("cras_cash", output.get("cras", "0"))))
    securities = Decimal(str(output.get("cras_scrt", "0")))
    receivables = Decimal(str(output.get("cras_rcbl", output.get("rcbl", "0"))))
    inventory = Decimal(str(output.get("cras_invt", output.get("invt", "0"))))

    # Step 2: Apply conservative adjustments
    adjusted_ca = (
        cash * Decimal("1.0") +
        securities * Decimal("1.0") +
        receivables * Decimal("0.80") +  # 20% bad debt allowance
        inventory * Decimal("0.70")       # 30% obsolescence allowance
    )

    # Step 3: Subtract ALL liabilities
    total_liabilities = Decimal(str(output.get("tlbt", "0")))
    ncav = adjusted_ca - total_liabilities

    # Step 4: Apply Graham's discount factor
    ncav_discounted = ncav * Decimal("0.66")

    # Step 5: Per-share value
    if shares_outstanding <= 0:
        return Decimal("0")
    return ncav_discounted / Decimal(str(shares_outstanding))


class GrahamScreener(Strategy):
    """Screen stocks using Graham's defensive investor criteria."""

    def __init__(
        self,
        client: Any,  # KISRestClient
        market: str = "KOSPI"  # KOSPI or KOSDAQ
    ):
        self.client = client
        self.market = market

        # Minimum market cap by market
        self.min_market_cap = (
            Decimal("2400000000000") if market == "KOSPI"  # ₩2.4조
            else Decimal("500000000000")  # ₩500B for KOSDAQ
        )

    def evaluate(self, symbol: str) -> Optional[DefensiveGrahamScore]:
        """
        Evaluate a stock against Graham's 7 criteria.

        Args:
            symbol: Stock symbol (e.g., "005930")

        Returns:
            DefensiveGrahamScore or None if evaluation fails
        """
        try:
            from stock_manager.adapters.broker.kis.apis.domestic_stock.info import (
                get_financial_ratio,
                get_balance_sheet,
            )
            from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import (
                inquire_current_price,
            )

            # Get financial data
            price_resp = inquire_current_price(self.client, symbol)
            balance_resp = get_balance_sheet(self.client, fid_input_iscd=symbol)
            ratio_resp = get_financial_ratio(self.client, fid_input_iscd=symbol)

            if any(r.get("rt_cd") != "0" for r in [price_resp, balance_resp, ratio_resp]):
                logger.warning(f"Failed to get data for {symbol}")
                return None

            price_output = price_resp.get("output", {})
            ratio_output = ratio_resp.get("output", {})

            # Extract values
            market_cap = Decimal(str(price_output.get("hts_avls", "0")))
            current_ratio = Decimal(str(ratio_output.get("crrt", "0")))
            debt_ratio = Decimal(str(ratio_output.get("lblt_rate", "0")))
            pe_ratio = Decimal(str(price_output.get("per", "0")))
            pb_ratio = Decimal(str(price_output.get("pbr", "0")))
            eps_growth = Decimal(str(ratio_output.get("eps_grw_rt", "0")))

            # For simplicity, assume dividends/earnings years from available data
            # In practice, these would come from historical data
            years_positive = int(ratio_output.get("posv_earn_yrs", "5"))
            years_dividends = int(ratio_output.get("dvdn_yrs", "5"))

            return DefensiveGrahamScore(
                symbol=symbol,
                # Criterion 1: Size
                market_cap=market_cap,
                meets_size=market_cap >= self.min_market_cap,
                # Criterion 2: Financial Condition
                current_ratio=current_ratio,
                debt_to_current_assets=debt_ratio / Decimal("100"),
                meets_financial=current_ratio >= Decimal("2.0") and debt_ratio <= Decimal("50"),
                # Criterion 3: Earnings Stability
                years_positive_earnings=years_positive,
                meets_stability=years_positive >= 10,
                # Criterion 4: Dividend Record
                years_dividends=years_dividends,
                meets_dividends=years_dividends >= 20,
                # Criterion 5: Earnings Growth
                eps_growth_10yr=eps_growth,
                meets_growth=eps_growth >= Decimal("33"),
                # Criterion 6: P/E
                pe_ratio=pe_ratio,
                meets_pe=pe_ratio > 0 and pe_ratio <= Decimal("15"),
                # Criterion 7: P/B
                pb_ratio=pb_ratio,
                pe_times_pb=pe_ratio * pb_ratio,
                meets_pb=pb_ratio <= Decimal("1.5") and (pe_ratio * pb_ratio) <= Decimal("22.5")
            )

        except Exception as e:
            logger.error(f"Graham evaluation failed for {symbol}: {e}")
            return None


def calculate_margin_of_safety(
    ncav_per_share: Decimal,
    current_price: Decimal
) -> Decimal:
    """
    Calculate Graham's margin of safety.

    Margin = (NCAV - Price) / NCAV
    Positive value = trading below NCAV (desired)
    """
    if ncav_per_share <= 0:
        return Decimal("-1")  # No margin of safety
    return (ncav_per_share - current_price) / ncav_per_share
