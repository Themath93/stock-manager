"""Thread safety tests for PositionManager."""
import threading
from decimal import Decimal


from stock_manager.trading.positions import PositionManager
from stock_manager.trading.models import Position


class TestPositionManagerThreadSafety:
    """Test that callbacks don't block other operations."""

    def test_callback_does_not_block_other_updates(self):
        """Callback execution should not block price updates from other threads."""
        # Given
        manager = PositionManager()
        callback_started = threading.Event()
        callback_can_finish = threading.Event()

        def slow_callback(symbol: str):
            callback_started.set()
            callback_can_finish.wait(timeout=5.0)  # Wait until allowed to finish

        manager.set_callbacks(on_stop_loss=slow_callback)

        # Create a position that will trigger stop-loss
        position = Position(
            symbol="TEST001",
            quantity=10,
            entry_price=Decimal("100"),
            current_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("110"),
        )
        manager.open_position(position)

        update_completed = threading.Event()

        def trigger_stop_loss():
            # This will trigger the slow callback
            manager.update_price("TEST001", Decimal("90"))

        def update_another_position():
            # Wait for callback to start
            callback_started.wait(timeout=2.0)
            # Try to update - should NOT block
            manager.open_position(Position(
                symbol="TEST002",
                quantity=5,
                entry_price=Decimal("50"),
                current_price=Decimal("50"),
            ))
            update_completed.set()

        # When
        t1 = threading.Thread(target=trigger_stop_loss)
        t2 = threading.Thread(target=update_another_position)

        t1.start()
        t2.start()

        # Then - update should complete while callback is running
        completed = update_completed.wait(timeout=1.0)

        # Allow callback to finish
        callback_can_finish.set()
        t1.join()
        t2.join()

        assert completed, "Update was blocked by callback execution"
