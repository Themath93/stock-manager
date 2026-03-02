from __future__ import annotations

import time
from datetime import datetime
from decimal import Decimal

from stock_manager.trading.indicators.cache import OHLCVCache
from stock_manager.trading.personas.models import MarketSnapshot


def _snapshot(symbol: str = "005930") -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        name="S",
        market="KOSPI",
        sector="tech",
        timestamp=datetime(2026, 1, 1),
        current_price=Decimal("100"),
        open_price=Decimal("99"),
        high_price=Decimal("101"),
        low_price=Decimal("98"),
        prev_close=Decimal("99"),
    )


def test_update_get_and_age() -> None:
    cache = OHLCVCache(ttl_seconds=5.0)
    snap = _snapshot("005930")

    assert cache.get("005930") is None
    assert cache.age("005930") is None

    cache.update("005930", snap)
    assert cache.get("005930") == snap
    assert cache.is_fresh("005930") is True

    age = cache.age("005930")
    assert age is not None
    assert age >= 0


def test_expiry_and_lazy_evict() -> None:
    cache = OHLCVCache(ttl_seconds=0.01)
    cache.update("005930", _snapshot("005930"))

    time.sleep(0.03)
    assert cache.is_fresh("005930") is False
    assert cache.get("005930") is None


def test_get_all_symbols_repr_and_clear() -> None:
    cache = OHLCVCache(ttl_seconds=5.0)
    cache.update("005930", _snapshot("005930"))
    cache.update("000660", _snapshot("000660"))

    all_items = cache.get_all()
    assert set(all_items) == {"005930", "000660"}
    assert cache.symbols() == ["000660", "005930"]
    assert len(cache) == 2

    representation = repr(cache)
    assert "OHLCVCache" in representation
    assert "005930" in representation

    cache.clear("005930")
    assert cache.get("005930") is None
    assert len(cache) == 1

    cache.clear()
    assert len(cache) == 0


def test_ttl_property_clamps_to_non_negative() -> None:
    cache = OHLCVCache(ttl_seconds=2.0)
    assert cache.ttl_seconds == 2.0

    cache.ttl_seconds = -1
    assert cache.ttl_seconds == 0.0
