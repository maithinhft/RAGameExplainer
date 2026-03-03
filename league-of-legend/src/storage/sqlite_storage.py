"""SQLite storage backend."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import aiosqlite

from src.storage.base import BaseStorage
from src.utils import get_logger

logger = get_logger("storage.sqlite")

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crawl_metadata (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    crawled_at  TEXT    NOT NULL,
    version     TEXT,
    language    TEXT,
    category    TEXT    NOT NULL,
    count       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS champions (
    champion_id     TEXT PRIMARY KEY,
    key             INTEGER,
    name            TEXT NOT NULL,
    title           TEXT,
    blurb           TEXT,
    lore            TEXT,
    tags            TEXT,  -- JSON array
    resource_type   TEXT,
    difficulty      INTEGER,
    attack          INTEGER,
    defense         INTEGER,
    magic           INTEGER,
    stats           TEXT,  -- JSON object
    spells          TEXT,  -- JSON array
    passive         TEXT,  -- JSON object
    skins           TEXT,  -- JSON array
    ally_tips       TEXT,  -- JSON array
    enemy_tips      TEXT,  -- JSON array
    image_filename  TEXT,
    version         TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_id             TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT,
    plaintext           TEXT,
    gold                TEXT,  -- JSON object
    tags                TEXT,  -- JSON array
    stats               TEXT,  -- JSON object
    from_items          TEXT,  -- JSON array
    into_items          TEXT,  -- JSON array
    maps                TEXT,  -- JSON object
    depth               INTEGER,
    image_filename      TEXT,
    required_champion   TEXT,
    required_ally       TEXT,
    in_store            INTEGER
);

CREATE TABLE IF NOT EXISTS rune_paths (
    path_id     INTEGER PRIMARY KEY,
    key         TEXT,
    name        TEXT NOT NULL,
    icon        TEXT,
    runes       TEXT  -- JSON array
);

CREATE TABLE IF NOT EXISTS runes (
    rune_id     INTEGER PRIMARY KEY,
    path_id     INTEGER,
    key         TEXT,
    name        TEXT NOT NULL,
    short_desc  TEXT,
    long_desc   TEXT,
    icon        TEXT,
    row         INTEGER,
    slot        INTEGER,
    FOREIGN KEY (path_id) REFERENCES rune_paths(path_id)
);

CREATE TABLE IF NOT EXISTS summoner_spells (
    spell_id        TEXT PRIMARY KEY,
    key             INTEGER,
    name            TEXT NOT NULL,
    description     TEXT,
    tooltip         TEXT,
    cooldown        TEXT,  -- JSON array
    cost            TEXT,  -- JSON array
    range           TEXT,  -- JSON array
    summoner_level  INTEGER,
    modes           TEXT,  -- JSON array
    image_filename  TEXT
);

CREATE TABLE IF NOT EXISTS maps (
    map_id          TEXT PRIMARY KEY,
    name            TEXT,
    image_filename  TEXT
);

CREATE TABLE IF NOT EXISTS patches (
    version     TEXT PRIMARY KEY,
    major       INTEGER,
    minor       INTEGER,
    patch       INTEGER
);
"""


class SqliteStorage(BaseStorage):
    """Save crawled data to a normalized SQLite database.

    Database is created at ``output_dir/lol_data.db``.
    """

    def __init__(self, output_dir: Path) -> None:
        super().__init__(output_dir)
        self._db_path = self.output_dir / "lol_data.db"
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(str(self._db_path))
            await self._db.executescript(SCHEMA_SQL)
            await self._db.commit()
        return self._db

    async def save(
        self,
        category: str,
        data: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        db = await self._ensure_db()

        # Record crawl metadata
        await db.execute(
            "INSERT INTO crawl_metadata (crawled_at, version, language, category, count) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                (metadata or {}).get("version", ""),
                (metadata or {}).get("language", ""),
                category,
                len(data),
            ),
        )

        # Category-specific inserts
        handler = getattr(self, f"_save_{category}", None)
        if handler:
            await handler(db, data)
        else:
            logger.warning("No SQLite handler for category: %s", category)

        await db.commit()
        logger.info("Saved [bold]%d[/] %s → %s", len(data), category, self._db_path)

    # ------------------------------------------------------------------
    # Category handlers
    # ------------------------------------------------------------------

    async def _save_champions(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for c in data:
            await db.execute(
                """INSERT OR REPLACE INTO champions
                   (champion_id, key, name, title, blurb, lore, tags, resource_type,
                    difficulty, attack, defense, magic, stats, spells, passive,
                    skins, ally_tips, enemy_tips, image_filename, version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    c["champion_id"], c["key"], c["name"], c["title"],
                    c["blurb"], c["lore"],
                    json.dumps(c["tags"]), c["resource_type"],
                    c["difficulty"], c["attack"], c["defense"], c["magic"],
                    json.dumps(c["stats"]), json.dumps(c["spells"]),
                    json.dumps(c["passive"]),
                    json.dumps(c["skins"]),
                    json.dumps(c["ally_tips"]), json.dumps(c["enemy_tips"]),
                    c["image_filename"], c["version"],
                ),
            )

    async def _save_items(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for i in data:
            await db.execute(
                """INSERT OR REPLACE INTO items
                   (item_id, name, description, plaintext, gold, tags, stats,
                    from_items, into_items, maps, depth, image_filename,
                    required_champion, required_ally, in_store)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    i["item_id"], i["name"], i["description"], i["plaintext"],
                    json.dumps(i["gold"]), json.dumps(i["tags"]),
                    json.dumps(i["stats"]),
                    json.dumps(i["from_items"]), json.dumps(i["into_items"]),
                    json.dumps(i["maps"]), i["depth"], i["image_filename"],
                    i["required_champion"], i["required_ally"],
                    1 if i["in_store"] else 0,
                ),
            )

    async def _save_runes(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for path in data:
            await db.execute(
                """INSERT OR REPLACE INTO rune_paths (path_id, key, name, icon, runes)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    path["path_id"], path["key"], path["name"],
                    path["icon"], json.dumps(path["runes"]),
                ),
            )
            for rune in path.get("runes", []):
                await db.execute(
                    """INSERT OR REPLACE INTO runes
                       (rune_id, path_id, key, name, short_desc, long_desc, icon, row, slot)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        rune["rune_id"], path["path_id"], rune["key"],
                        rune["name"], rune["short_desc"], rune["long_desc"],
                        rune["icon"], rune["row"], rune["slot"],
                    ),
                )

    async def _save_spells(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for s in data:
            await db.execute(
                """INSERT OR REPLACE INTO summoner_spells
                   (spell_id, key, name, description, tooltip, cooldown, cost,
                    range, summoner_level, modes, image_filename)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    s["spell_id"], s["key"], s["name"], s["description"],
                    s["tooltip"], json.dumps(s["cooldown"]),
                    json.dumps(s["cost"]), json.dumps(s["range"]),
                    s["summoner_level"], json.dumps(s["modes"]),
                    s["image_filename"],
                ),
            )

    async def _save_maps(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for m in data:
            await db.execute(
                "INSERT OR REPLACE INTO maps (map_id, name, image_filename) VALUES (?, ?, ?)",
                (m["map_id"], m["name"], m["image_filename"]),
            )

    async def _save_patches(self, db: aiosqlite.Connection, data: list[dict]) -> None:
        for p in data:
            await db.execute(
                "INSERT OR REPLACE INTO patches (version, major, minor, patch) VALUES (?, ?, ?, ?)",
                (p["version"], p["major"], p["minor"], p["patch"]),
            )

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
