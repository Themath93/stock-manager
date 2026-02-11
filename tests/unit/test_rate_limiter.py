"""Unit tests for rate limiter."""
import time
import threading
from stock_manager.trading.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test RateLimiter thread-safe operations."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=20, window_seconds=1.0)
        assert limiter.max_requests == 20
        assert limiter.window == 1.0
        assert limiter.available == 20

    def test_default_initialization(self):
        """Test default rate limiter parameters."""
        limiter = RateLimiter()
        assert limiter.max_requests == 20
        assert limiter.window == 1.0

    def test_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        for _ in range(5):
            assert limiter.try_acquire() is True

    def test_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=1.0)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_available_count(self):
        """Test available request count."""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        assert limiter.available == 5

        limiter.try_acquire()
        assert limiter.available == 4

        limiter.try_acquire()
        assert limiter.available == 3

    def test_available_resets_after_window(self):
        """Test that available count resets after time window."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.1)

        # Use up the limit
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.available == 0

        # Wait for window to expire
        time.sleep(0.15)

        # Should be available again
        assert limiter.available == 2
        assert limiter.try_acquire() is True

    def test_try_acquire_non_blocking(self):
        """Test that try_acquire doesn't block."""
        limiter = RateLimiter(max_requests=1, window_seconds=1.0)

        # First request succeeds
        assert limiter.try_acquire() is True

        # Second request fails immediately
        start = time.time()
        assert limiter.try_acquire() is False
        elapsed = time.time() - start

        # Should return almost immediately (< 10ms)
        assert elapsed < 0.01

    def test_acquire_blocks_until_available(self):
        """Test that acquire blocks until request is available."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.2)

        # Use up the limit
        assert limiter.try_acquire() is True

        # acquire should block until window expires
        start = time.time()
        result = limiter.acquire(timeout=0.3)
        elapsed = time.time() - start

        assert result is True
        # Should have waited approximately 0.2 seconds
        assert 0.15 < elapsed < 0.35

    def test_acquire_timeout(self):
        """Test that acquire respects timeout."""
        limiter = RateLimiter(max_requests=1, window_seconds=1.0)

        # Use up the limit
        assert limiter.try_acquire() is True

        # Try to acquire with short timeout
        start = time.time()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.time() - start

        assert result is False
        # Should timeout after approximately 0.1 seconds
        assert elapsed < 0.2

    def test_acquire_no_timeout(self):
        """Test that acquire waits indefinitely without timeout."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)

        # Use up the limit
        assert limiter.try_acquire() is True

        # acquire without timeout should eventually succeed
        result = limiter.acquire(timeout=None)
        assert result is True

    def test_reset(self):
        """Test rate limiter reset."""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)

        # Use up some requests
        limiter.try_acquire()
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.available == 2

        # Reset
        limiter.reset()
        assert limiter.available == 5

    def test_sliding_window(self):
        """Test sliding window behavior."""
        limiter = RateLimiter(max_requests=3, window_seconds=0.2)

        # Make 3 requests
        for _ in range(3):
            assert limiter.try_acquire() is True

        # Should be rate limited
        assert limiter.try_acquire() is False

        # Wait for first request to expire
        time.sleep(0.15)

        # Still rate limited (requests haven't fully expired)
        assert limiter.try_acquire() is False

        # Wait a bit more
        time.sleep(0.1)

        # Now should be available
        assert limiter.try_acquire() is True

    def test_thread_safety_concurrent_acquire(self):
        """Test thread safety with concurrent acquires."""
        limiter = RateLimiter(max_requests=10, window_seconds=0.1)
        success_count = []
        errors = []

        def worker():
            try:
                if limiter.try_acquire():
                    success_count.append(1)
            except Exception as e:
                errors.append(e)

        # Create 20 threads trying to acquire
        threads = [threading.Thread(target=worker) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 10 should succeed (the limit)
        assert len(success_count) == 10
        assert len(errors) == 0

    def test_thread_safety_concurrent_check_available(self):
        """Test thread safety when checking available count."""
        limiter = RateLimiter(max_requests=20, window_seconds=0.5)
        results = []
        errors = []

        def worker():
            try:
                for _ in range(10):
                    limiter.try_acquire()
                    available = limiter.available
                    results.append(available)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0
        # Results should be non-negative
        assert all(r >= 0 for r in results)

    def test_multiple_windows(self):
        """Test behavior across multiple time windows."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.1)

        # First window
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

        # Wait for window to pass
        time.sleep(0.15)

        # Second window
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_partial_window_expiry(self):
        """Test that requests expire individually as time passes."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.2)

        # Make first request
        assert limiter.try_acquire() is True
        assert limiter.available == 1

        # Wait a bit
        time.sleep(0.1)

        # Make second request
        assert limiter.try_acquire() is True
        assert limiter.available == 0

        # Wait for first request to expire
        time.sleep(0.15)

        # First request expired, one slot available
        assert limiter.available == 1
        assert limiter.try_acquire() is True

    def test_high_rate_limit(self):
        """Test with high rate limit similar to KIS API."""
        limiter = RateLimiter(max_requests=20, window_seconds=1.0)

        # Should allow 20 requests
        for _ in range(20):
            assert limiter.try_acquire() is True

        # 21st should be blocked
        assert limiter.try_acquire() is False

    def test_acquire_with_immediate_availability(self):
        """Test that acquire returns immediately when available."""
        limiter = RateLimiter(max_requests=5, window_seconds=1.0)

        start = time.time()
        result = limiter.acquire(timeout=1.0)
        elapsed = time.time() - start

        assert result is True
        # Should return almost immediately
        assert elapsed < 0.01

    def test_zero_window_edge_case(self):
        """Test behavior with very small window."""
        limiter = RateLimiter(max_requests=5, window_seconds=0.01)

        # Should still enforce limit
        for _ in range(5):
            assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

        # Should recover quickly
        time.sleep(0.02)
        assert limiter.try_acquire() is True

    def test_available_property_is_consistent(self):
        """Test that available property gives consistent results."""
        limiter = RateLimiter(max_requests=10, window_seconds=1.0)

        # Available should match reality
        assert limiter.available == 10

        for i in range(5):
            limiter.try_acquire()
            assert limiter.available == 10 - (i + 1)

    def test_acquire_releases_on_timeout(self):
        """Test that failed acquire doesn't consume a slot."""
        limiter = RateLimiter(max_requests=1, window_seconds=1.0)

        # Use the slot
        assert limiter.try_acquire() is True

        # Try to acquire with timeout (should fail)
        assert limiter.acquire(timeout=0.05) is False

        # Available should still be 0 (not negative)
        assert limiter.available == 0
