"""Version / patch crawler."""

from __future__ import annotations

from config import settings as cfg
from src.crawlers.base import BaseCrawler
from src.models.patch import PatchVersion
from src.utils import get_logger

logger = get_logger("crawlers.version")


class VersionCrawler(BaseCrawler[PatchVersion]):
    """Fetches all available Data Dragon version strings."""

    name = "Version"

    async def crawl(self) -> list[PatchVersion]:
        self._log_start()
        data: list[str] = await self.client.get_json(cfg.VERSIONS_URL)
        versions = [PatchVersion.from_string(v) for v in data]
        self._log_done(len(versions))
        return versions

    async def get_latest_version(self) -> str:
        """Return the latest version string from Data Dragon."""
        data: list[str] = await self.client.get_json(cfg.VERSIONS_URL)
        if not data:
            raise RuntimeError("Could not fetch versions from Data Dragon")
        latest = data[0]
        logger.info("Latest Data Dragon version: [bold yellow]%s[/]", latest)
        return latest
