"""
Central configuration for the League of Legends data crawler.
All constants, URLs, defaults, and tunable parameters live here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Data Dragon base URLs
# ---------------------------------------------------------------------------
DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
DDRAGON_CDN = f"{DDRAGON_BASE}/cdn"
DDRAGON_API = f"{DDRAGON_BASE}/api"

VERSIONS_URL = f"{DDRAGON_API}/versions.json"

# Template URLs — call .format(version=..., lang=...)
CHAMPION_LIST_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/champion.json"
CHAMPION_DETAIL_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/champion/{{champion_id}}.json"
ITEM_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/item.json"
RUNE_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/runesReforged.json"
SUMMONER_SPELL_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/summoner.json"
MAP_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/map.json"
PROFILE_ICON_URL = f"{DDRAGON_CDN}/{{version}}/data/{{lang}}/profileicon.json"

# Image URL templates
CHAMPION_SQUARE_IMG = f"{DDRAGON_CDN}/{{version}}/img/champion/{{image_filename}}"
CHAMPION_LOADING_IMG = f"{DDRAGON_CDN}/img/champion/loading/{{champion_id}}_{{skin_num}}.jpg"
CHAMPION_SPLASH_IMG = f"{DDRAGON_CDN}/img/champion/splash/{{champion_id}}_{{skin_num}}.jpg"
ITEM_IMG = f"{DDRAGON_CDN}/{{version}}/img/item/{{image_filename}}"
SPELL_IMG = f"{DDRAGON_CDN}/{{version}}/img/spell/{{image_filename}}"
PASSIVE_IMG = f"{DDRAGON_CDN}/{{version}}/img/passive/{{image_filename}}"

# Supported languages
SUPPORTED_LANGUAGES = [
    "en_US", "vi_VN", "ko_KR", "ja_JP", "zh_CN", "zh_TW",
    "es_ES", "fr_FR", "de_DE", "pt_BR", "ru_RU", "th_TH",
]

# ---------------------------------------------------------------------------
# Runtime settings
# ---------------------------------------------------------------------------
OutputFormat = Literal["json", "sqlite", "both"]


@dataclass
class Settings:
    """Runtime configuration — created once and threaded through the app."""

    # Data selection
    version: str | None = None  # None → auto-detect latest
    language: str = "en_US"

    # What to crawl
    crawl_champions: bool = False
    crawl_items: bool = False
    crawl_runes: bool = False
    crawl_spells: bool = False
    crawl_maps: bool = False
    crawl_patches: bool = False
    crawl_all: bool = False
    download_images: bool = False

    # Output
    output_format: OutputFormat = "json"
    output_dir: Path = field(default_factory=lambda: Path("data"))

    # HTTP tuning
    max_concurrency: int = 10
    max_retries: int = 3
    retry_base_delay: float = 1.0  # seconds, exponential backoff
    request_timeout: int = 30  # seconds
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.cache_dir = Path(self.cache_dir)
        if self.crawl_all:
            self.crawl_champions = True
            self.crawl_items = True
            self.crawl_runes = True
            self.crawl_spells = True
            self.crawl_maps = True
            self.crawl_patches = True

    @property
    def should_crawl_anything(self) -> bool:
        return any([
            self.crawl_champions,
            self.crawl_items,
            self.crawl_runes,
            self.crawl_spells,
            self.crawl_maps,
            self.crawl_patches,
        ])
