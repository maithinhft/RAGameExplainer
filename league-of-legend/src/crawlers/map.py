"""Map metadata crawler."""

from __future__ import annotations

from typing import Any

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.utils import get_logger

logger = get_logger("crawlers.map")


class MapCrawler(BaseCrawler[dict]):
    """Crawl map metadata from Data Dragon."""

    name = "Map"

    async def crawl(self) -> list[dict]:
        self._log_start()

        url = self._build_url(cfg.MAP_URL)
        raw = await self.client.get_json(url)

        maps_data: dict[str, Any] = raw.get("data", {})
        maps: list[dict] = []
        for map_id, map_data in maps_data.items():
            maps.append({
                "map_id": map_id,
                "name": map_data.get("MapName", ""),
                "image_filename": map_data.get("image", {}).get("full", ""),
            })

        self._log_done(len(maps))
        return maps
