"""
Market Data Poller

Discovers candidate stocks from market data and filters them based on
screening criteria. Implements WT-002: Market Data Polling.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

from ..domain.worker import Candidate
from ..adapters.broker.port import BrokerPort

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data for a single stock"""

    symbol: str  # Stock symbol
    name: str  # Stock name
    price: Decimal  # Current price
    change: Decimal  # Price change
    change_percent: Decimal  # Price change percentage
    volume: int  # Trading volume
    timestamp: datetime  # Data timestamp


@dataclass
class ScreeningCriteria:
    """Criteria for candidate screening"""

    min_volume: Optional[int] = None  # Minimum trading volume
    max_change_percent: Optional[Decimal] = None  # Maximum price change percentage
    min_change_percent: Optional[Decimal] = None  # Minimum price change percentage
    price_range: Optional[tuple[Decimal, Decimal]] = None  # Price range (min, max)
    exclude_symbols: Optional[set[str]] = None  # Symbols to exclude
    custom_filters: Optional[list[Callable[[MarketData], bool]]] = None  # Custom filter functions


class BrokerPortNotFoundError(Exception):
    """Broker port not found"""

    pass


class MarketDataPoller:
    """Market Data Poller

    Polls market data, discovers candidate stocks, and filters them
    based on screening criteria.
    """

    def __init__(
        self,
        broker: BrokerPort,
        default_screening_criteria: Optional[ScreeningCriteria] = None,
    ):
        """Initialize Market Data Poller

        Args:
            broker: Broker port for market data
            default_screening_criteria: Default screening criteria
        """
        self.broker = broker
        self.default_screening_criteria = default_screening_criteria or ScreeningCriteria()

    async def discover_candidates(
        self,
        criteria: Optional[ScreeningCriteria] = None,
        max_candidates: int = 100,
    ) -> list[Candidate]:
        """Discover candidate stocks from market data

        Args:
            criteria: Screening criteria (default: default_screening_criteria)
            max_candidates: Maximum number of candidates to return

        Returns:
            list[Candidate]: List of candidate stocks

        Raises:
            BrokerPortNotFoundError: If broker port is not available
        """
        criteria = criteria or self.default_screening_criteria

        # Fetch market data from broker
        market_data_list = await self._fetch_market_data()

        # Filter candidates based on criteria
        candidates = []
        for market_data in market_data_list:
            if self._screen_market_data(market_data, criteria):
                candidate = self._create_candidate(market_data)
                candidates.append(candidate)

                if len(candidates) >= max_candidates:
                    break

        logger.info(f"Discovered {len(candidates)} candidates from {len(market_data_list)} stocks")
        return candidates

    async def _fetch_market_data(self) -> list[MarketData]:
        """Fetch market data from broker

        Returns:
            list[MarketData]: List of market data
        """
        try:
            # TODO: Implement actual broker market data fetching
            # This is a placeholder - actual implementation will depend on
            # broker API capabilities

            # Placeholder: Return empty list
            logger.warning("Market data fetching not yet implemented - returning empty list")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return []

    def _screen_market_data(
        self,
        market_data: MarketData,
        criteria: ScreeningCriteria,
    ) -> bool:
        """Screen market data against criteria

        Args:
            market_data: Market data to screen
            criteria: Screening criteria

        Returns:
            bool: True if market data passes screening
        """
        # Check volume criteria
        if criteria.min_volume and market_data.volume < criteria.min_volume:
            return False

        # Check change percent criteria
        if criteria.max_change_percent and market_data.change_percent > criteria.max_change_percent:
            return False

        if criteria.min_change_percent and market_data.change_percent < criteria.min_change_percent:
            return False

        # Check price range criteria
        if criteria.price_range:
            min_price, max_price = criteria.price_range
            if not (min_price <= market_data.price <= max_price):
                return False

        # Check exclude symbols
        if criteria.exclude_symbols and market_data.symbol in criteria.exclude_symbols:
            return False

        # Check custom filters
        if criteria.custom_filters:
            for custom_filter in criteria.custom_filters:
                if not custom_filter(market_data):
                    return False

        return True

    def _create_candidate(self, market_data: MarketData) -> Candidate:
        """Create Candidate from MarketData

        Args:
            market_data: Market data

        Returns:
            Candidate: Candidate stock
        """
        return Candidate(
            symbol=market_data.symbol,
            name=market_data.name,
            current_price=market_data.price,
            volume=market_data.volume,
            change_percent=market_data.change_percent,
            discovered_at=datetime.utcnow(),
            metadata={
                "change": float(market_data.change),
                "timestamp": market_data.timestamp.isoformat(),
            },
        )
