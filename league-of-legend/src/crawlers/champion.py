"""Champion crawler — fetches all champions with full detail data."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.models.champion import Champion
from src.utils import get_logger

logger = get_logger("crawlers.champion")


class ChampionCrawler(BaseCrawler[Champion]):
    """Crawl champion list then fetch each champion's detailed data in parallel."""

    name = "Champion"

    async def crawl(self) -> list[Champion]:
        self._log_start()

        # Step 1: Get champion list
        list_url = self._build_url(cfg.CHAMPION_LIST_URL)
        list_data = await self.client.get_json(list_url)
        champion_ids: list[str] = list(list_data.get("data", {}).keys())
        logger.info("Found [bold]%d[/] champions — fetching details...", len(champion_ids))

        # Step 2: Fetch each champion's detail page in parallel
        detail_urls = [
            self._build_url(cfg.CHAMPION_DETAIL_URL, champion_id=cid)
            for cid in champion_ids
        ]
        detail_responses = await self.client.get_many_json_ordered(detail_urls)

        # Step 3: Parse into Champion objects
        champions: list[Champion] = []
        for cid, response in zip(champion_ids, detail_responses):
            if response is None:
                logger.warning("Failed to fetch detail for champion: %s", cid)
                continue
            try:
                champ_data = response.get("data", {}).get(cid, {})
                if champ_data:
                    champions.append(Champion.from_detail_data(champ_data))
            except Exception as exc:
                logger.error("Failed to parse champion %s: %s", cid, exc)

        # Step 4 (optional): Download images
        if self.settings.download_images:
            await self._download_images(champions)

        self._log_done(len(champions))
        return champions

    async def _download_images(self, champions: list[Champion]) -> None:
        """Download champion square icons and loading screen images."""
        img_dir = self.settings.output_dir / "images" / "champions"
        img_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for champ in champions:
            if champ.image_filename:
                url = self._build_url(
                    cfg.CHAMPION_SQUARE_IMG,
                    image_filename=champ.image_filename,
                )
                dest = img_dir / champ.image_filename
                tasks.append(self.client.download_file(url, dest))

            # Download loading screen for default skin
            loading_url = cfg.CHAMPION_LOADING_IMG.format(
                champion_id=champ.champion_id, skin_num=0
            )
            loading_dest = img_dir / f"{champ.champion_id}_loading.jpg"
            tasks.append(self.client.download_file(loading_url, loading_dest))

        if tasks:
            logger.info("Downloading %d champion images...", len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Champion images downloaded to [bold]%s[/]", img_dir)
