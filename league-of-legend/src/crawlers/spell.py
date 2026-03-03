"""Summoner Spell crawler."""

from __future__ import annotations

import asyncio
from typing import Any

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.models.spell import SummonerSpell
from src.utils import get_logger

logger = get_logger("crawlers.spell")


class SpellCrawler(BaseCrawler[SummonerSpell]):
    """Crawl all summoner spells from Data Dragon."""

    name = "Summoner Spell"

    async def crawl(self) -> list[SummonerSpell]:
        self._log_start()

        url = self._build_url(cfg.SUMMONER_SPELL_URL)
        raw = await self.client.get_json(url)

        spells_data: dict[str, Any] = raw.get("data", {})
        spells: list[SummonerSpell] = []
        for spell_data in spells_data.values():
            try:
                spells.append(SummonerSpell.from_dict(spell_data))
            except Exception as exc:
                logger.error("Failed to parse summoner spell: %s", exc)

        # Optional: download spell images
        if self.settings.download_images:
            await self._download_images(spells)

        self._log_done(len(spells))
        return spells

    async def _download_images(self, spells: list[SummonerSpell]) -> None:
        """Download summoner spell icons."""
        img_dir = self.settings.output_dir / "images" / "spells"
        img_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for spell in spells:
            if spell.image_filename:
                url = self._build_url(
                    cfg.SPELL_IMG, image_filename=spell.image_filename
                )
                dest = img_dir / spell.image_filename
                tasks.append(self.client.download_file(url, dest))

        if tasks:
            logger.info("Downloading %d spell images...", len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)
