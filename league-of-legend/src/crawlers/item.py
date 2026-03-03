"""Item crawler."""

from __future__ import annotations

import asyncio
from typing import Any

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.models.item import Item
from src.utils import get_logger

logger = get_logger("crawlers.item")


class ItemCrawler(BaseCrawler[Item]):
    """Crawl all in-game items from Data Dragon."""

    name = "Item"

    async def crawl(self) -> list[Item]:
        self._log_start()

        url = self._build_url(cfg.ITEM_URL)
        raw = await self.client.get_json(url)

        items_data: dict[str, Any] = raw.get("data", {})
        items: list[Item] = []
        for item_id, item_data in items_data.items():
            try:
                items.append(Item.from_dict(item_id, item_data))
            except Exception as exc:
                logger.error("Failed to parse item %s: %s", item_id, exc)

        # Optional: download item images
        if self.settings.download_images:
            await self._download_images(items)

        self._log_done(len(items))
        return items

    async def _download_images(self, items: list[Item]) -> None:
        """Download item icons."""
        img_dir = self.settings.output_dir / "images" / "items"
        img_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for item in items:
            if item.image_filename:
                url = self._build_url(
                    cfg.ITEM_IMG, image_filename=item.image_filename
                )
                dest = img_dir / item.image_filename
                tasks.append(self.client.download_file(url, dest))

        if tasks:
            logger.info("Downloading %d item images...", len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Item images downloaded to [bold]%s[/]", img_dir)
