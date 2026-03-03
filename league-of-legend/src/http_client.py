"""Async HTTP client with retry, concurrency control, and disk caching."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import aiohttp

from src.utils import get_logger

logger = get_logger("http_client")


class HttpClient:
    """Reusable async HTTP client wrapping :mod:`aiohttp`.

    Features
    --------
    * **Exponential-backoff retry** — configurable attempts and base delay.
    * **Concurrency semaphore** — prevents overwhelming the target server.
    * **Disk-based response cache** — keyed by URL hash; skips network when
      a cached response exists and ``use_cache`` is *True*.
    * **Progress callback** — optional callable invoked after each request.
    """

    def __init__(
        self,
        max_concurrency: int = 10,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        request_timeout: int = 30,
        cache_dir: Path | None = None,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._timeout = aiohttp.ClientTimeout(total=request_timeout)
        self._cache_dir = cache_dir
        self._session: aiohttp.ClientSession | None = None

        # Stats
        self.requests_made: int = 0
        self.cache_hits: int = 0
        self.errors: int = 0

        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "HttpClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"Accept": "application/json"},
            )

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{self._url_hash(url)}.json"

    def _read_cache(self, url: str) -> dict | list | None:
        path = self._cache_path(url)
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.cache_hits += 1
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _write_cache(self, url: str, data: Any) -> None:
        path = self._cache_path(url)
        if path:
            try:
                path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except OSError as exc:
                logger.warning("Failed to write cache for %s: %s", url, exc)

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def get_json(
        self,
        url: str,
        *,
        use_cache: bool = True,
    ) -> Any:
        """Fetch JSON from *url* with retry and optional caching.

        Args:
            url: Target URL.
            use_cache: When *True*, check disk cache before making a request
                       and store the response on success.

        Returns:
            Parsed JSON (dict or list).

        Raises:
            aiohttp.ClientError: After exhausting all retry attempts.
        """
        # Check cache first
        if use_cache:
            cached = self._read_cache(url)
            if cached is not None:
                logger.debug("Cache hit: %s", url)
                return cached

        await self._ensure_session()
        assert self._session is not None

        last_exc: Exception | None = None

        async with self._semaphore:
            for attempt in range(1, self._max_retries + 1):
                try:
                    self.requests_made += 1
                    async with self._session.get(url) as resp:
                        resp.raise_for_status()
                        data = await resp.json(content_type=None)

                        if use_cache:
                            self._write_cache(url, data)

                        return data

                except (
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    json.JSONDecodeError,
                ) as exc:
                    last_exc = exc
                    self.errors += 1
                    if attempt < self._max_retries:
                        delay = self._retry_base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Request failed (attempt %d/%d) %s — retrying in %.1fs: %s",
                            attempt,
                            self._max_retries,
                            url,
                            delay,
                            exc,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "Request failed after %d attempts: %s — %s",
                            self._max_retries,
                            url,
                            exc,
                        )

        raise last_exc  # type: ignore[misc]

    async def download_file(
        self,
        url: str,
        dest: Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Download a binary file (e.g. image) to *dest*.

        Args:
            url: Target URL.
            dest: Destination file path.
            overwrite: When *False*, skip the download if *dest* already exists.

        Returns:
            The destination ``Path``.
        """
        if not overwrite and dest.exists():
            return dest

        await self._ensure_session()
        assert self._session is not None

        dest.parent.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            for attempt in range(1, self._max_retries + 1):
                try:
                    self.requests_made += 1
                    async with self._session.get(url) as resp:
                        resp.raise_for_status()
                        content = await resp.read()
                        dest.write_bytes(content)
                        return dest
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    self.errors += 1
                    if attempt < self._max_retries:
                        delay = self._retry_base_delay * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Download failed: %s — %s", url, exc)
                        raise

        return dest  # unreachable, but keeps mypy happy

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    async def get_many_json(
        self,
        urls: list[str],
        *,
        use_cache: bool = True,
    ) -> list[Any]:
        """Fetch multiple URLs concurrently.

        Returns:
            List of parsed JSON responses, in the same order as *urls*.
            Failed requests return ``None`` instead of raising.
        """
        tasks = [self.get_json(url, use_cache=use_cache) for url in urls]
        results: list[Any] = []
        for coro in asyncio.as_completed(tasks):
            try:
                results.append(await coro)
            except Exception:
                results.append(None)

        # as_completed doesn't preserve order — re-fetch to keep order
        ordered: list[Any] = []
        for url in urls:
            try:
                ordered.append(await self.get_json(url, use_cache=True))
            except Exception:
                ordered.append(None)
        return ordered

    async def get_many_json_ordered(
        self,
        urls: list[str],
        *,
        use_cache: bool = True,
    ) -> list[Any]:
        """Fetch multiple URLs concurrently, preserving order.

        Returns:
            List of parsed JSON results in the same order as *urls*.
            Failed requests return ``None``.
        """
        async def _safe_get(url: str) -> Any:
            try:
                return await self.get_json(url, use_cache=use_cache)
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", url, exc)
                return None

        return await asyncio.gather(*[_safe_get(url) for url in urls])

    def stats_summary(self) -> str:
        """Return a human-readable summary of request statistics."""
        return (
            f"Requests: {self.requests_made} | "
            f"Cache hits: {self.cache_hits} | "
            f"Errors: {self.errors}"
        )
