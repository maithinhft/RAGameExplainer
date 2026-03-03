#!/usr/bin/env python3
"""
League of Legends Data Crawler
===============================

Production-quality crawler for League of Legends game data using
Riot's Data Dragon (DDragon) API. No API key required.

Usage:
    python main.py --all                    # Crawl everything
    python main.py --champions --items      # Specific categories
    python main.py --version 16.4.1         # Specific patch version
    python main.py --lang vi_VN             # Vietnamese language
    python main.py --output sqlite          # SQLite output
    python main.py --download-images        # Download images too
    python main.py --all --output both      # JSON + SQLite
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import Settings
from src.http_client import HttpClient
from src.crawlers import (
    VersionCrawler,
    ChampionCrawler,
    ItemCrawler,
    RuneCrawler,
    SpellCrawler,
    MapCrawler,
)
from src.storage import JsonStorage, SqliteStorage
from src.utils import setup_logger, get_logger

console = Console()
logger = get_logger()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="lol-crawler",
        description="🎮 League of Legends Data Crawler — powered by Riot Data Dragon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    Crawl all available data
  %(prog)s --champions --items      Crawl only champions and items
  %(prog)s --all --lang vi_VN       Crawl in Vietnamese
  %(prog)s --all --output sqlite    Save to SQLite database
  %(prog)s --all --download-images  Also download images
  %(prog)s --all --version 15.24.1  Crawl a specific patch version
        """,
    )

    # What to crawl
    crawl_group = parser.add_argument_group("Data categories")
    crawl_group.add_argument("--all", action="store_true", help="Crawl all categories")
    crawl_group.add_argument("--champions", action="store_true", help="Crawl champion data")
    crawl_group.add_argument("--items", action="store_true", help="Crawl item data")
    crawl_group.add_argument("--runes", action="store_true", help="Crawl rune data")
    crawl_group.add_argument("--spells", action="store_true", help="Crawl summoner spell data")
    crawl_group.add_argument("--maps", action="store_true", help="Crawl map metadata")
    crawl_group.add_argument("--patches", action="store_true", help="Crawl patch/version history")

    # Options
    opt_group = parser.add_argument_group("Options")
    opt_group.add_argument("--version", type=str, default=None,
                           help="Specific DDragon version (default: latest)")
    opt_group.add_argument("--lang", type=str, default="en_US",
                           help="Language code (default: en_US). Try vi_VN for Vietnamese")
    opt_group.add_argument("--output", type=str, choices=["json", "sqlite", "both"],
                           default="json", help="Output format (default: json)")
    opt_group.add_argument("--output-dir", type=str, default="data",
                           help="Output directory (default: data)")
    opt_group.add_argument("--download-images", action="store_true",
                           help="Download champion/item/spell images")
    opt_group.add_argument("--no-cache", action="store_true",
                           help="Disable HTTP response caching")
    opt_group.add_argument("--concurrency", type=int, default=10,
                           help="Max concurrent HTTP requests (default: 10)")
    opt_group.add_argument("--verbose", action="store_true", help="Enable debug logging")

    return parser.parse_args()


async def run(settings: Settings) -> None:
    """Main crawl orchestration."""
    start_time = time.monotonic()

    # Print banner
    console.print(Panel.fit(
        "[bold cyan]🎮 League of Legends Data Crawler[/]\n"
        f"[dim]Language: {settings.language} | Output: {settings.output_format} | "
        f"Dir: {settings.output_dir}[/]",
        border_style="cyan",
    ))

    # Create HTTP client
    client = HttpClient(
        max_concurrency=settings.max_concurrency,
        max_retries=settings.max_retries,
        retry_base_delay=settings.retry_base_delay,
        request_timeout=settings.request_timeout,
        cache_dir=settings.cache_dir if not settings.verbose else None,
    )

    # Create storage backends
    storages = []
    if settings.output_format in ("json", "both"):
        storages.append(JsonStorage(settings.output_dir))
    if settings.output_format in ("sqlite", "both"):
        storages.append(SqliteStorage(settings.output_dir))

    async with client:
        # Resolve version
        version_crawler = VersionCrawler(client, settings)
        if settings.version:
            resolved_version = settings.version
            logger.info("Using specified version: [bold yellow]%s[/]", resolved_version)
        else:
            resolved_version = await version_crawler.get_latest_version()

        # Set version on all crawlers
        crawler_map = {}

        if settings.crawl_patches:
            version_crawler.version = resolved_version
            crawler_map["patches"] = version_crawler

        if settings.crawl_champions:
            c = ChampionCrawler(client, settings)
            c.version = resolved_version
            crawler_map["champions"] = c

        if settings.crawl_items:
            c = ItemCrawler(client, settings)
            c.version = resolved_version
            crawler_map["items"] = c

        if settings.crawl_runes:
            c = RuneCrawler(client, settings)
            c.version = resolved_version
            crawler_map["runes"] = c

        if settings.crawl_spells:
            c = SpellCrawler(client, settings)
            c.version = resolved_version
            crawler_map["spells"] = c

        if settings.crawl_maps:
            c = MapCrawler(client, settings)
            c.version = resolved_version
            crawler_map["maps"] = c

        if not crawler_map:
            console.print("[yellow]⚠ No categories selected. Use --all or specify categories.[/]")
            console.print("[dim]Run with --help for usage information.[/]")
            return

        # Execute crawls
        results: dict[str, list] = {}
        for category, crawler in crawler_map.items():
            try:
                data = await crawler.crawl()
                results[category] = data
            except Exception as exc:
                logger.error("Failed to crawl %s: %s", category, exc, exc_info=settings.verbose)

        # Serialize and save
        metadata = {"version": resolved_version, "language": settings.language}

        for category, data in results.items():
            if not data:
                continue

            # Convert model objects to dicts
            if hasattr(data[0], "to_dict"):
                serialized = [item.to_dict() for item in data]
            else:
                serialized = data  # Already dicts (e.g. maps)

            for storage in storages:
                try:
                    await storage.save(category, serialized, metadata=metadata)
                except Exception as exc:
                    logger.error("Failed to save %s: %s", category, exc, exc_info=True)

    # Close storage backends
    for storage in storages:
        await storage.close()

    # Print summary
    elapsed = time.monotonic() - start_time
    _print_summary(results, client, elapsed, resolved_version)


def _print_summary(
    results: dict[str, list],
    client: HttpClient,
    elapsed: float,
    version: str,
) -> None:
    """Print a rich summary table."""
    table = Table(title=f"📊 Crawl Summary — v{version}", border_style="green")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Count", style="bold green", justify="right")

    total = 0
    for category, data in results.items():
        count = len(data)
        total += count
        table.add_row(category.capitalize(), str(count))

    table.add_section()
    table.add_row("[bold]Total[/]", f"[bold]{total}[/]")

    console.print()
    console.print(table)
    console.print(f"\n[dim]⏱  Completed in {elapsed:.1f}s | {client.stats_summary()}[/]")


def main() -> None:
    """Entry point."""
    args = parse_args()

    # Build settings from CLI args
    settings = Settings(
        version=args.version,
        language=args.lang,
        crawl_champions=args.champions,
        crawl_items=args.items,
        crawl_runes=args.runes,
        crawl_spells=args.spells,
        crawl_maps=args.maps,
        crawl_patches=args.patches,
        crawl_all=args.all,
        download_images=args.download_images,
        output_format=args.output,
        output_dir=Path(args.output_dir),
        max_concurrency=args.concurrency,
        verbose=args.verbose,
        log_level="DEBUG" if args.verbose else "INFO",
        cache_dir=Path(".cache") if not args.no_cache else Path("/tmp/lol_no_cache"),
    )

    # Setup logging
    setup_logger(level=settings.log_level)

    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Crawl interrupted by user.[/]")
        sys.exit(130)
    except Exception as exc:
        console.print(f"\n[bold red]✗ Fatal error:[/] {exc}")
        if settings.verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
