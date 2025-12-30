"""Tests for TokenBatcher."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time

import pytest

from server.streaming.token_batcher import TokenBatcher


# =============================================================================
# TokenBatcher Tests
# =============================================================================


class TestTokenBatcher:
    """Tests for TokenBatcher class."""

    @pytest.fixture
    def broadcast_tracker(self):
        """Track broadcast calls."""

        class Tracker:
            def __init__(self):
                self.calls: list[str] = []
                self.call_times: list[float] = []

            async def broadcast(self, tokens: str) -> None:
                self.calls.append(tokens)
                self.call_times.append(time.time())

        return Tracker()

    @pytest.mark.asyncio
    async def test_batch_size_triggers_flush(self, broadcast_tracker):
        """Test that reaching batch size triggers flush."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=5,
            max_delay_ms=1000.0,  # High delay so we don't trigger on time
        )

        # Add tokens up to batch size
        await batcher.add_token("H")  # 1
        await batcher.add_token("e")  # 2
        await batcher.add_token("l")  # 3
        await batcher.add_token("l")  # 4
        assert len(broadcast_tracker.calls) == 0  # Not yet flushed

        await batcher.add_token("o")  # 5 - should flush
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "Hello"

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self, broadcast_tracker):
        """Test that flush clears the buffer."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=10,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("test")
        assert batcher.pending == "test"

        await batcher.flush()
        assert batcher.pending == ""
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "test"

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_no_broadcast(self, broadcast_tracker):
        """Test that flushing empty buffer does not broadcast."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=5,
            max_delay_ms=50.0,
        )

        await batcher.flush()
        assert len(broadcast_tracker.calls) == 0

    @pytest.mark.asyncio
    async def test_max_delay_triggers_flush(self, broadcast_tracker):
        """Test that exceeding max delay triggers flush."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=100,  # High batch size
            max_delay_ms=50.0,  # 50ms delay
        )

        await batcher.add_token("A")
        assert len(broadcast_tracker.calls) == 0

        # Wait for delay to trigger
        await asyncio.sleep(0.06)  # 60ms

        await batcher.add_token("B")
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "AB"

    @pytest.mark.asyncio
    async def test_multiple_flushes(self, broadcast_tracker):
        """Test multiple flush cycles."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=3,
            max_delay_ms=1000.0,
        )

        # First batch
        await batcher.add_token("A")
        await batcher.add_token("B")
        await batcher.add_token("C")
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "ABC"

        # Second batch
        await batcher.add_token("D")
        await batcher.add_token("E")
        await batcher.add_token("F")
        assert len(broadcast_tracker.calls) == 2
        assert broadcast_tracker.calls[1] == "DEF"

    @pytest.mark.asyncio
    async def test_pending_property(self, broadcast_tracker):
        """Test pending property shows buffered content."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=100,  # Large batch size to prevent auto-flush
            max_delay_ms=60000.0,  # Very long delay to prevent time-based flush
        )

        assert batcher.pending == ""

        await batcher.add_token("Hello")
        assert batcher.pending == "Hello"

        await batcher.add_token(" ")
        assert batcher.pending == "Hello "

        await batcher.add_token("World")
        assert batcher.pending == "Hello World"

    @pytest.mark.asyncio
    async def test_multi_character_tokens(self, broadcast_tracker):
        """Test with multi-character tokens."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=10,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("Hello")  # 5 chars
        await batcher.add_token(" ")  # 6 chars
        await batcher.add_token("World")  # 11 chars - should flush

        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "Hello World"

    @pytest.mark.asyncio
    async def test_large_single_token_immediate_flush(self, broadcast_tracker):
        """Test that a single large token triggers immediate flush."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=5,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("This is a very long token")
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "This is a very long token"

    @pytest.mark.asyncio
    async def test_final_flush_gets_remaining(self, broadcast_tracker):
        """Test that final flush sends remaining buffered tokens."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=100,  # Large batch size to prevent auto-flush
            max_delay_ms=60000.0,  # Very long delay to prevent time-based flush
        )

        await batcher.add_token("incomplete")
        assert batcher.pending == "incomplete"
        assert len(broadcast_tracker.calls) == 0

        # Manual flush at end
        await batcher.flush()
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "incomplete"
        assert batcher.pending == ""

    @pytest.mark.asyncio
    async def test_flush_resets_timer(self, broadcast_tracker):
        """Test that flush resets the delay timer."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=100,
            max_delay_ms=50.0,
        )

        # Add token and wait almost to delay
        await batcher.add_token("A")
        await asyncio.sleep(0.04)  # 40ms

        # Force flush resets timer
        await batcher.flush()
        assert len(broadcast_tracker.calls) == 1

        # Add more tokens - should not immediately flush
        await batcher.add_token("B")
        await batcher.add_token("C")

        # Wait less than delay
        await asyncio.sleep(0.03)  # 30ms
        await batcher.add_token("D")

        # Should not have flushed yet (only 30ms since last flush)
        assert len(broadcast_tracker.calls) == 1

    @pytest.mark.asyncio
    async def test_concurrent_token_additions(self, broadcast_tracker):
        """Test adding tokens concurrently."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=10,
            max_delay_ms=1000.0,
        )

        # Add tokens concurrently
        async def add_tokens(prefix: str, count: int):
            for i in range(count):
                await batcher.add_token(f"{prefix}{i}")

        await asyncio.gather(
            add_tokens("A", 3),
            add_tokens("B", 3),
        )

        await batcher.flush()

        # All tokens should be captured (order may vary)
        combined = "".join(broadcast_tracker.calls)
        for i in range(3):
            assert f"A{i}" in combined
            assert f"B{i}" in combined

    @pytest.mark.asyncio
    async def test_empty_token_handling(self, broadcast_tracker):
        """Test handling of empty tokens."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=5,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("")
        await batcher.add_token("")
        await batcher.add_token("X")

        await batcher.flush()
        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == "X"

    @pytest.mark.asyncio
    async def test_whitespace_token_handling(self, broadcast_tracker):
        """Test handling of whitespace tokens."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=5,
            max_delay_ms=1000.0,
        )

        await batcher.add_token(" ")
        await batcher.add_token("\n")
        await batcher.add_token("\t")
        await batcher.add_token("X")
        await batcher.add_token("Y")

        assert len(broadcast_tracker.calls) == 1
        assert broadcast_tracker.calls[0] == " \n\tXY"


class TestTokenBatcherEdgeCases:
    """Edge case tests for TokenBatcher."""

    @pytest.fixture
    def broadcast_tracker(self):
        """Track broadcast calls."""

        class Tracker:
            def __init__(self):
                self.calls: list[str] = []

            async def broadcast(self, tokens: str) -> None:
                self.calls.append(tokens)

        return Tracker()

    @pytest.mark.asyncio
    async def test_batch_size_one(self, broadcast_tracker):
        """Test with batch size of 1 (immediate flush)."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=1,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("A")
        await batcher.add_token("B")
        await batcher.add_token("C")

        assert len(broadcast_tracker.calls) == 3
        assert broadcast_tracker.calls == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_zero_delay(self, broadcast_tracker):
        """Test with zero max delay (immediate flush on any token)."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=100,
            max_delay_ms=0.0,
        )

        await batcher.add_token("A")
        # Should flush immediately due to zero delay
        assert len(broadcast_tracker.calls) == 1

    @pytest.mark.asyncio
    async def test_unicode_tokens(self, broadcast_tracker):
        """Test handling of unicode tokens."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=10,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("Hello")
        await batcher.add_token(" ")
        await batcher.add_token("World")

        await batcher.flush()
        assert broadcast_tracker.calls[0] == "Hello World"

    @pytest.mark.asyncio
    async def test_special_characters(self, broadcast_tracker):
        """Test handling of special characters."""
        batcher = TokenBatcher(
            broadcast_fn=broadcast_tracker.broadcast,
            batch_size=20,
            max_delay_ms=1000.0,
        )

        await batcher.add_token("<action>")
        await batcher.add_token("fold")
        await batcher.add_token("</action>")

        await batcher.flush()
        assert broadcast_tracker.calls[0] == "<action>fold</action>"


class TestTokenBatcherBroadcastFailure:
    """Tests for broadcast failure handling."""

    @pytest.mark.asyncio
    async def test_broadcast_exception_propagates(self):
        """Test that broadcast exceptions propagate."""

        async def failing_broadcast(tokens: str) -> None:
            raise RuntimeError("Broadcast failed")

        batcher = TokenBatcher(
            broadcast_fn=failing_broadcast,
            batch_size=1,
            max_delay_ms=1000.0,
        )

        with pytest.raises(RuntimeError, match="Broadcast failed"):
            await batcher.add_token("test")
