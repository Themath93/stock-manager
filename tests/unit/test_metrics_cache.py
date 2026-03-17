"""Specification tests for DailyRiskMetricsCache.

Each test documents an expected behavior of the compute-once-daily cache.
"""

from datetime import date

from stock_manager.trading.risk.metrics_cache import DailyRiskMetricsCache


class TestDailyRiskMetricsCache:
    """DailyRiskMetricsCache behavior specifications."""

    def test_compute_fn_called_once_then_cached(self):
        """get_or_compute() calls compute_fn once; subsequent calls return cached value."""
        cache = DailyRiskMetricsCache()
        call_count = 0

        def expensive():
            nonlocal call_count
            call_count += 1
            return 42

        assert cache.get_or_compute("metric_a", expensive) == 42
        assert cache.get_or_compute("metric_a", expensive) == 42
        assert call_count == 1

    def test_cache_invalidates_on_new_day(self):
        """Cache auto-invalidates when the date changes."""
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("k", lambda: "day1")

        # Simulate day change by backdating _computed_date
        cache._computed_date = date(2020, 1, 1)

        result = cache.get_or_compute("k", lambda: "day2")
        assert result == "day2"

    def test_invalidate_all_clears_entire_cache(self):
        """invalidate() with no key clears everything and resets computed date."""
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("a", lambda: 1)
        cache.get_or_compute("b", lambda: 2)

        cache.invalidate()

        # Both keys should be recomputed
        assert cache.get_or_compute("a", lambda: 10) == 10
        assert cache.get_or_compute("b", lambda: 20) == 20

    def test_invalidate_specific_key_preserves_others(self):
        """invalidate(key) removes only that key; other entries remain cached."""
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("a", lambda: 1)
        cache.get_or_compute("b", lambda: 2)

        cache.invalidate("a")

        assert cache.get_or_compute("a", lambda: 10) == 10  # recomputed
        assert cache.get_or_compute("b", lambda: 99) == 2  # still cached

    def test_is_stale_true_when_empty(self):
        """is_stale is True when cache has no computed date."""
        cache = DailyRiskMetricsCache()
        assert cache.is_stale is True

    def test_is_stale_false_after_compute(self):
        """is_stale is False immediately after computing a value today."""
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("k", lambda: 1)
        assert cache.is_stale is False

    def test_is_stale_true_after_day_change(self):
        """is_stale detects when computed date no longer matches today."""
        cache = DailyRiskMetricsCache()
        cache.get_or_compute("k", lambda: 1)

        # Simulate date was yesterday
        cache._computed_date = date(2020, 1, 1)
        assert cache.is_stale is True
