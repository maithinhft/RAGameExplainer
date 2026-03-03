"""Rune (Runes Reforged) crawler."""

from __future__ import annotations

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.models.rune import RunePath
from src.utils import get_logger

logger = get_logger("crawlers.rune")


class RuneCrawler(BaseCrawler[RunePath]):
    """Crawl all rune paths and their rune slots from Data Dragon."""

    name = "Rune"

    async def crawl(self) -> list[RunePath]:
        self._log_start()

        url = self._build_url(cfg.RUNE_URL)
        raw: list[dict] = await self.client.get_json(url)

        paths: list[RunePath] = []
        for path_data in raw:
            try:
                paths.append(RunePath.from_dict(path_data))
            except Exception as exc:
                logger.error("Failed to parse rune path: %s", exc)

        total_runes = sum(len(p.runes) for p in paths)
        logger.info("Parsed %d rune paths with %d total runes", len(paths), total_runes)

        self._log_done(len(paths))
        return paths
