"""Thread safety tests for PriceMonitor."""
import threading
import time
from unittest.mock import MagicMock
from unittest.mock import patch


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

    def test_polling_with_concurrent_symbol_updates(self):
        """Polling loop should tolerate concurrent symbol add/remove updates."""
        monitor = PriceMonitor(client=MagicMock(), interval=0.01)
        callback_count = 0
        callback_lock = threading.Lock()

        def on_price(symbol, price):
            nonlocal callback_count
            with callback_lock:
                callback_count += 1

        with patch(
            "stock_manager.adapters.broker.kis.apis.domestic_stock.basic.inquire_current_price",
            return_value={"rt_cd": "0", "output": {"stck_prpr": "70000"}},
        ):
            monitor.start(["005930"], on_price)
            for i in range(20):
                monitor.add_symbol(f"SYM{i:03d}")
                monitor.remove_symbol(f"SYM{i:03d}")
            time.sleep(0.05)
            monitor.stop()

        assert callback_count >= 1
