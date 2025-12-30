"""Token batching for efficient WebSocket streaming."""

import asyncio
import time
from typing import Awaitable, Callable


class TokenBatcher:
    """Batch tokens before broadcasting to reduce WebSocket messages."""

    def __init__(
        self,
        broadcast_fn: Callable[[str], Awaitable[None]],
        batch_size: int = 5,
        max_delay_ms: float = 50.0,
    ):
        """
        Initialize token batcher.

        Args:
            broadcast_fn: Async function to call with batched tokens
            batch_size: Number of characters to batch before flush
            max_delay_ms: Maximum delay before flush in milliseconds
        """
        self.broadcast_fn = broadcast_fn
        self.batch_size = batch_size
        self.max_delay_ms = max_delay_ms
        self._buffer = ""
        self._last_flush = time.time()

    async def add_token(self, token: str) -> None:
        """Add a token to the buffer, flushing if needed."""
        self._buffer += token

        should_flush = (
            len(self._buffer) >= self.batch_size
            or (time.time() - self._last_flush) * 1000 >= self.max_delay_ms
        )

        if should_flush:
            await self.flush()

    async def flush(self) -> None:
        """Flush the buffer, broadcasting accumulated tokens."""
        if self._buffer:
            await self.broadcast_fn(self._buffer)
            self._buffer = ""
            self._last_flush = time.time()

    @property
    def pending(self) -> str:
        """Get pending tokens in buffer."""
        return self._buffer
