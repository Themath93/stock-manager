"""Advanced risk management package.

Re-exports core risk types for backward compatibility, plus new
advanced risk management components.
"""

from stock_manager.trading.risk.manager import (
    RiskManager,
    RiskLimits,
    RiskCheckResult,
    calculate_kelly_position_size,
)
from stock_manager.trading.risk.circuit_breaker import CircuitBreakerManager
from stock_manager.trading.risk.sector_exposure import (
    SectorExposureSnapshot,
    compute_sector_exposure,
    Position as RiskPosition,
)
from stock_manager.trading.risk.volatility_sizing import compute_volatility_position_size
from stock_manager.trading.risk.metrics_cache import DailyRiskMetricsCache

__all__ = [
    # Core (backward-compatible)
    "RiskManager",
    "RiskLimits",
    "RiskCheckResult",
    "calculate_kelly_position_size",
    # Advanced
    "CircuitBreakerManager",
    "SectorExposureSnapshot",
    "compute_sector_exposure",
    "RiskPosition",
    "compute_volatility_position_size",
    "DailyRiskMetricsCache",
]
