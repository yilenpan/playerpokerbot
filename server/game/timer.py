"""Turn timer for human players."""

import asyncio
import time
from typing import Awaitable, Callable, Optional


class TurnTimer:
    """Server-authoritative turn timer."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.start_time: Optional[float] = None
        self._timeout_task: Optional[asyncio.Task] = None
        self._tick_task: Optional[asyncio.Task] = None
        self._cancelled = False

    async def start(
        self,
        on_timeout: Callable[[], Awaitable[None]],
        on_tick: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> None:
        """
        Start the timer.

        Args:
            on_timeout: Called when timer expires
            on_tick: Called every second with remaining time
        """
        self._cancelled = False
        self.start_time = time.time()

        # Start timeout task
        self._timeout_task = asyncio.create_task(self._wait_and_timeout(on_timeout))

        # Start tick task if callback provided
        if on_tick:
            self._tick_task = asyncio.create_task(self._tick_loop(on_tick))

    async def cancel(self) -> None:
        """Cancel the timer (player acted in time)."""
        self._cancelled = True

        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
            self._timeout_task = None

        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
            self._tick_task = None

        self.start_time = None

    async def _wait_and_timeout(
        self,
        on_timeout: Callable[[], Awaitable[None]],
    ) -> None:
        """Wait for timeout then call callback."""
        try:
            await asyncio.sleep(self.timeout_seconds)
            if not self._cancelled:
                await on_timeout()
        except asyncio.CancelledError:
            pass

    async def _tick_loop(
        self,
        on_tick: Callable[[int], Awaitable[None]],
    ) -> None:
        """Send tick updates every second."""
        try:
            while not self._cancelled:
                remaining = self.get_remaining()
                await on_tick(remaining)
                if remaining <= 0:
                    break
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    def get_remaining(self) -> int:
        """Get remaining seconds."""
        if self.start_time is None:
            return self.timeout_seconds
        elapsed = time.time() - self.start_time
        return max(0, int(self.timeout_seconds - elapsed))

    @property
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self.start_time is not None and not self._cancelled
