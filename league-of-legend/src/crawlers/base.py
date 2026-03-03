"""Abstract base crawler class."""

from __future__ import annotations

import abc
from typing import Any, Generic, TypeVar

from config.settings import Settings
from src.http_client import HttpClient
from src.utils import get_logger

T = TypeVar("T")

logger = get_logger("crawlers.base")


class BaseCrawler(abc.ABC, Generic[T]):
    """Abstract base class for all data crawlers.

    Subclasses must implement :meth:`crawl` to fetch, parse, and return
    a list of typed model objects.
    """

    name: str = "base"

    def __init__(self, client: HttpClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self.version: str = ""  # resolved before crawl

    @abc.abstractmethod
    async def crawl(self) -> list[T]:
        """Execute the crawl and return parsed model objects."""
        ...

    def _build_url(self, template: str, **kwargs: str) -> str:
        """Format a URL template with version and language defaults."""
        return template.format(
            version=kwargs.get("version", self.version),
            lang=kwargs.get("lang", self.settings.language),
            **{k: v for k, v in kwargs.items() if k not in ("version", "lang")},
        )

    def _log_start(self) -> None:
        logger.info("[bold cyan]Starting %s crawler[/] (v%s, %s)",
                     self.name, self.version, self.settings.language)

    def _log_done(self, count: int) -> None:
        logger.info("[bold green]%s crawler finished[/] — %d items collected",
                     self.name, count)
