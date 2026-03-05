"""
Request Queue — Async semaphore-based queue for LLM requests.

Ensures only 1 LLM call runs at a time. Other requests wait in queue.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class QueueStats:
    """Tracks queue performance."""

    total_queued: int = 0
    total_processed: int = 0
    total_timeout: int = 0
    current_waiting: int = 0
    max_wait_time: float = 0.0
    avg_wait_time: float = 0.0
    _wait_times: list[float] = field(default_factory=list, repr=False)

    def record_wait(self, wait_time: float) -> None:
        self._wait_times.append(wait_time)
        if wait_time > self.max_wait_time:
            self.max_wait_time = wait_time
        self.avg_wait_time = sum(self._wait_times) / len(self._wait_times)

    def to_dict(self) -> dict:
        return {
            "total_queued": self.total_queued,
            "total_processed": self.total_processed,
            "total_timeout": self.total_timeout,
            "current_waiting": self.current_waiting,
            "max_wait_seconds": round(self.max_wait_time, 2),
            "avg_wait_seconds": round(self.avg_wait_time, 2),
        }


class RequestQueue:
    """Async request queue with semaphore to limit concurrent LLM calls.

    Usage::

        queue = RequestQueue(max_concurrent=1, timeout=120)

        async def handle_request():
            async with queue.acquire():
                result = await call_llm(prompt)
            return result
    """

    def __init__(
        self,
        max_concurrent: int = 1,
        timeout: float = 120.0,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = QueueStats()

    class _AcquireContext:
        """Async context manager for queue acquisition."""

        def __init__(self, queue: "RequestQueue") -> None:
            self._queue = queue
            self._start_time = 0.0

        async def __aenter__(self) -> None:
            self._queue.stats.total_queued += 1
            self._queue.stats.current_waiting += 1
            self._start_time = time.monotonic()

            try:
                await asyncio.wait_for(
                    self._queue._semaphore.acquire(),
                    timeout=self._queue.timeout,
                )
            except asyncio.TimeoutError:
                self._queue.stats.current_waiting -= 1
                self._queue.stats.total_timeout += 1
                raise TimeoutError(
                    f"Request queued > {self._queue.timeout}s. "
                    f"LLM server quá tải, vui lòng thử lại sau."
                )

            wait_time = time.monotonic() - self._start_time
            self._queue.stats.current_waiting -= 1
            self._queue.stats.record_wait(wait_time)

        async def __aexit__(self, *args) -> None:
            self._queue._semaphore.release()
            self._queue.stats.total_processed += 1

    def acquire(self) -> _AcquireContext:
        """Acquire a slot in the queue. Use as async context manager."""
        return self._AcquireContext(self)
