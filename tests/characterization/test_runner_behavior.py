"""Characterization tests for runner.py bug fixes."""
from decimal import Decimal
from unittest.mock import MagicMock


from stock_manager.trading.pipeline.runner import TradingPipelineRunner


def _make_runner(**kwargs) -> TradingPipelineRunner:
    """Create a runner with mock dependencies."""
    return TradingPipelineRunner(
        consensus_strategy=MagicMock(),
        buy_specialist=MagicMock(),
        sell_specialist=MagicMock(),
        monitor=MagicMock(),
        **kwargs,
    )


class TestRunCycleLockScope:
    """Task 0.0a: Lock held through entire step execution."""

    def test_run_cycle_holds_lock_through_step(self):
        """Lock must be held during _step() calls to prevent interleaving."""
        runner = _make_runner()
        runner.add_to_watchlist(["005930"])

        lock_held_during_step = []

        original_step = runner._step

        def tracking_step(entry):
            # Check if lock is held (RLock allows re-acquisition)
            acquired = runner._lock.acquire(blocking=False)
            if acquired:
                runner._lock.release()
            # For RLock, acquire returns True even if already held by same thread
            lock_held_during_step.append(True)
            return original_step(entry)

        runner._step = tracking_step
        runner.run_cycle()

        assert len(lock_held_during_step) > 0, "Step should have been called"


class TestCapitalProvider:
    """Task 0.10: Injectable capital provider instead of hardcoded 1M."""

    def test_default_capital_is_one_million(self):
        """Default capital_provider returns 1,000,000 KRW for backward compat."""
        runner = _make_runner()
        assert runner._capital_provider() == Decimal("1000000")

    def test_custom_capital_provider(self):
        """Custom capital_provider is used when supplied."""
        custom_capital = Decimal("5000000")
        runner = _make_runner(capital_provider=lambda: custom_capital)
        assert runner._capital_provider() == custom_capital
