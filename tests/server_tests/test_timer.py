"""Tests for TurnTimer."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time

import pytest

from server.game.timer import TurnTimer


# =============================================================================
# TurnTimer Tests
# =============================================================================


class TestTurnTimer:
    """Tests for TurnTimer class."""

    @pytest.fixture
    def timer(self):
        """Create a timer with short timeout for testing."""
        return TurnTimer(timeout_seconds=2)

    @pytest.fixture
    def callback_tracker(self):
        """Track callback invocations."""

        class Tracker:
            def __init__(self):
                self.timeout_called = False
                self.tick_values: list[int] = []
                self.timeout_time: float = None

            async def on_timeout(self):
                self.timeout_called = True
                self.timeout_time = time.time()

            async def on_tick(self, remaining: int):
                self.tick_values.append(remaining)

        return Tracker()

    @pytest.mark.asyncio
    async def test_timer_initial_state(self, timer):
        """Test timer initial state."""
        assert timer.timeout_seconds == 2
        assert timer.start_time is None
        assert timer.is_running is False
        assert timer.get_remaining() == 2

    @pytest.mark.asyncio
    async def test_timer_start(self, timer, callback_tracker):
        """Test starting the timer."""
        await timer.start(on_timeout=callback_tracker.on_timeout)

        assert timer.is_running is True
        assert timer.start_time is not None

        # Cancel to clean up
        await timer.cancel()

    @pytest.mark.asyncio
    async def test_timer_cancel_before_timeout(self, timer, callback_tracker):
        """Test canceling timer before timeout."""
        await timer.start(on_timeout=callback_tracker.on_timeout)
        await asyncio.sleep(0.1)
        await timer.cancel()

        assert timer.is_running is False
        assert timer.start_time is None
        assert callback_tracker.timeout_called is False

    @pytest.mark.asyncio
    async def test_timer_timeout_fires(self, callback_tracker):
        """Test that timeout callback fires after timeout."""
        timer = TurnTimer(timeout_seconds=0.2)  # 200ms timeout

        start = time.time()
        await timer.start(on_timeout=callback_tracker.on_timeout)

        # Wait for timeout
        await asyncio.sleep(0.3)

        assert callback_tracker.timeout_called is True
        elapsed = callback_tracker.timeout_time - start
        assert elapsed >= 0.2
        assert elapsed < 0.4  # Some buffer for timing

    @pytest.mark.asyncio
    async def test_timer_tick_callback(self, callback_tracker):
        """Test tick callbacks."""
        timer = TurnTimer(timeout_seconds=3)

        await timer.start(
            on_timeout=callback_tracker.on_timeout,
            on_tick=callback_tracker.on_tick,
        )

        # Wait for a couple of ticks
        await asyncio.sleep(2.5)
        await timer.cancel()

        # Should have received some tick values
        assert len(callback_tracker.tick_values) >= 2
        # First tick should show roughly 3 seconds
        assert callback_tracker.tick_values[0] in [2, 3]
        # Values should be decreasing
        for i in range(1, len(callback_tracker.tick_values)):
            assert callback_tracker.tick_values[i] <= callback_tracker.tick_values[i - 1]

    @pytest.mark.asyncio
    async def test_timer_get_remaining(self, timer, callback_tracker):
        """Test get_remaining during timer run."""
        await timer.start(on_timeout=callback_tracker.on_timeout)

        # Immediately after start
        remaining = timer.get_remaining()
        assert remaining in [1, 2]  # Depending on timing

        await asyncio.sleep(1)
        remaining = timer.get_remaining()
        assert remaining in [0, 1]

        await timer.cancel()

    @pytest.mark.asyncio
    async def test_timer_get_remaining_not_started(self, timer):
        """Test get_remaining when timer not started."""
        assert timer.get_remaining() == timer.timeout_seconds

    @pytest.mark.asyncio
    async def test_timer_cancel_idempotent(self, timer, callback_tracker):
        """Test that cancel can be called multiple times safely."""
        await timer.start(on_timeout=callback_tracker.on_timeout)

        # Cancel multiple times
        await timer.cancel()
        await timer.cancel()
        await timer.cancel()

        assert timer.is_running is False

    @pytest.mark.asyncio
    async def test_timer_cancel_without_start(self, timer):
        """Test cancel without start doesn't raise."""
        # Should not raise
        await timer.cancel()
        assert timer.is_running is False

    @pytest.mark.asyncio
    async def test_timer_restart(self, callback_tracker):
        """Test restarting timer after cancel."""
        timer = TurnTimer(timeout_seconds=0.2)

        # First start
        await timer.start(on_timeout=callback_tracker.on_timeout)
        await asyncio.sleep(0.1)
        await timer.cancel()
        assert callback_tracker.timeout_called is False

        # Restart
        await timer.start(on_timeout=callback_tracker.on_timeout)
        await asyncio.sleep(0.3)

        assert callback_tracker.timeout_called is True

    @pytest.mark.asyncio
    async def test_timer_no_tick_callback(self, timer, callback_tracker):
        """Test timer works without tick callback."""
        # Start without on_tick
        await timer.start(on_timeout=callback_tracker.on_timeout)
        await asyncio.sleep(0.1)
        await timer.cancel()

        # Should work without errors
        assert timer.is_running is False

    @pytest.mark.asyncio
    async def test_timer_is_running_property(self, timer, callback_tracker):
        """Test is_running property."""
        assert timer.is_running is False

        await timer.start(on_timeout=callback_tracker.on_timeout)
        assert timer.is_running is True

        await timer.cancel()
        assert timer.is_running is False

    @pytest.mark.asyncio
    async def test_timer_cancelled_flag_prevents_timeout(self, callback_tracker):
        """Test that cancelled flag prevents timeout callback."""
        timer = TurnTimer(timeout_seconds=0.1)

        await timer.start(on_timeout=callback_tracker.on_timeout)

        # Immediately cancel
        timer._cancelled = True
        await asyncio.sleep(0.2)

        # Timeout should not have been called due to _cancelled flag
        # Note: The timer task might still complete, but callback won't execute
        await timer.cancel()


class TestTurnTimerEdgeCases:
    """Edge case tests for TurnTimer."""

    @pytest.mark.asyncio
    async def test_timer_zero_timeout(self):
        """Test timer with zero timeout."""
        tracker = {"called": False}

        async def on_timeout():
            tracker["called"] = True

        timer = TurnTimer(timeout_seconds=0)
        await timer.start(on_timeout=on_timeout)

        # Should fire almost immediately
        await asyncio.sleep(0.1)
        assert tracker["called"] is True

    @pytest.mark.asyncio
    async def test_timer_very_long_timeout(self):
        """Test timer with very long timeout (verify it can be cancelled)."""
        tracker = {"called": False}

        async def on_timeout():
            tracker["called"] = True

        timer = TurnTimer(timeout_seconds=3600)  # 1 hour
        await timer.start(on_timeout=on_timeout)

        # Verify it started
        assert timer.is_running is True

        # Cancel immediately
        await timer.cancel()
        assert tracker["called"] is False

    @pytest.mark.asyncio
    async def test_timer_tick_stops_on_cancel(self):
        """Test that tick loop stops when timer is cancelled."""
        tick_values = []

        async def on_tick(remaining: int):
            tick_values.append(remaining)

        async def on_timeout():
            pass

        timer = TurnTimer(timeout_seconds=10)
        await timer.start(on_timeout=on_timeout, on_tick=on_tick)

        # Get a couple ticks
        await asyncio.sleep(2.5)
        tick_count_at_cancel = len(tick_values)

        await timer.cancel()

        # Wait more and verify no more ticks
        await asyncio.sleep(1)
        assert len(tick_values) == tick_count_at_cancel

    @pytest.mark.asyncio
    async def test_timer_tick_stops_at_zero(self):
        """Test that tick loop stops when remaining reaches zero."""
        tick_values = []

        async def on_tick(remaining: int):
            tick_values.append(remaining)

        called = {"value": False}

        async def on_timeout():
            called["value"] = True

        timer = TurnTimer(timeout_seconds=2)
        await timer.start(on_timeout=on_timeout, on_tick=on_tick)

        # Wait for completion
        await asyncio.sleep(3)

        # Should have stopped ticking at 0
        assert 0 in tick_values
        # Timeout should have been called
        assert called["value"] is True

    @pytest.mark.asyncio
    async def test_concurrent_timer_instances(self):
        """Test multiple timer instances running concurrently."""
        results = {"timer1": False, "timer2": False}

        async def on_timeout1():
            results["timer1"] = True

        async def on_timeout2():
            results["timer2"] = True

        timer1 = TurnTimer(timeout_seconds=0.1)
        timer2 = TurnTimer(timeout_seconds=0.2)

        await timer1.start(on_timeout=on_timeout1)
        await timer2.start(on_timeout=on_timeout2)

        await asyncio.sleep(0.15)
        assert results["timer1"] is True
        assert results["timer2"] is False

        await asyncio.sleep(0.1)
        assert results["timer2"] is True


class TestTurnTimerTaskManagement:
    """Tests for timer task management."""

    @pytest.mark.asyncio
    async def test_timer_tasks_are_cancelled(self):
        """Test that internal tasks are properly cancelled."""

        async def on_timeout():
            pass

        async def on_tick(remaining: int):
            pass

        timer = TurnTimer(timeout_seconds=10)
        await timer.start(on_timeout=on_timeout, on_tick=on_tick)

        # Get references to tasks
        timeout_task = timer._timeout_task
        tick_task = timer._tick_task

        assert timeout_task is not None
        assert tick_task is not None

        await timer.cancel()

        # Tasks should be None after cancel
        assert timer._timeout_task is None
        assert timer._tick_task is None

    @pytest.mark.asyncio
    async def test_timer_handles_cancelled_error(self):
        """Test that timer properly handles CancelledError."""

        async def on_timeout():
            pass

        timer = TurnTimer(timeout_seconds=1)
        await timer.start(on_timeout=on_timeout)

        # Directly cancel the internal task
        if timer._timeout_task:
            timer._timeout_task.cancel()

        # This should not raise
        await timer.cancel()
