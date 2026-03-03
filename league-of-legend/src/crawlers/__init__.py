from src.crawlers.base import BaseCrawler
from src.crawlers.version import VersionCrawler
from src.crawlers.champion import ChampionCrawler
from src.crawlers.item import ItemCrawler
from src.crawlers.rune import RuneCrawler
from src.crawlers.spell import SpellCrawler
from src.crawlers.map import MapCrawler

__all__ = [
    "BaseCrawler",
    "VersionCrawler",
    "ChampionCrawler",
    "ItemCrawler",
    "RuneCrawler",
    "SpellCrawler",
    "MapCrawler",
]
