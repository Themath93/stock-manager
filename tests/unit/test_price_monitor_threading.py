"""Thread safety tests for PriceMonitor."""
import threading
from unittest.mock import MagicMock


from stock_manager.monitoring.price_monitor import PriceMonitor


class TestPriceMonitorThreadSafety:
    """Test concurrent access to PriceMonitor symbols list."""

    def test_add_remove_symbol_concurrent_no_crash(self):
        """Concurrent add/remove operations should not crash."""
        # Given
        mock_client = MagicMock()
        monitor = PriceMonitor(
            client=mock_client,
            interval=1.0,
        )
        errors = []

        def add_symbols():
            try:
                for i in range(100):
                    monitor.add_symbol(f"SYM{i:03d}")
            except Exception as e:
                errors.append(e)

        def remove_symbols():
            try:
                for i in range(100):
                    monitor.remove_symbol(f"SYM{i:03d}")
            except Exception as e:
                errors.append(e)

        # When - run add and remove concurrently
        threads = [
            threading.Thread(target=add_symbols),
            threading.Thread(target=remove_symbols),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Then - no exceptions should have occurred
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
