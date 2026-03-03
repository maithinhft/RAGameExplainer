"""
Indexer — Load crawled LoL JSON data and build a searchable document corpus.

Each champion / item / rune / spell / patch is flattened into a Document
with a searchable text representation and a reference to the raw data.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Document:
    """A single searchable document in the index."""

    doc_id: str
    category: str          # "champion", "item", "rune", "spell", "map", "patch"
    title: str             # Human-readable name
    content: str           # Flattened text for search
    raw_data: dict[str, Any] = field(default_factory=dict, repr=False)
    keywords: list[str] = field(default_factory=list)  # Exact-match keywords


def _strip_html(text: str) -> str:
    """Remove HTML tags from DDragon descriptions."""
    return re.sub(r"<[^>]+>", "", text)


def _safe_join(items: list, sep: str = ", ") -> str:
    return sep.join(str(i) for i in items) if items else ""


class Indexer:
    """Build a searchable document corpus from crawled League of Legends data.

    Usage::

        indexer = Indexer(data_dir=Path("league-of-legend/data"))
        indexer.build()
        print(f"Indexed {len(indexer.documents)} documents")
    """

    def __init__(self, data_dir: Path | str = "league-of-legend/data") -> None:
        self.data_dir = Path(data_dir)
        self.documents: list[Document] = []

    def build(self) -> list[Document]:
        """Load all data files and build the document index."""
        self.documents = []

        loaders = [
            ("champions.json", self._index_champions),
            ("items.json", self._index_items),
            ("runes.json", self._index_runes),
            ("spells.json", self._index_spells),
            ("maps.json", self._index_maps),
            ("patches.json", self._index_patches),
        ]

        for filename, loader in loaders:
            filepath = self.data_dir / filename
            if filepath.exists():
                try:
                    raw = json.loads(filepath.read_text(encoding="utf-8"))
                    data_list = raw.get("data", [])
                    loader(data_list)
                except (json.JSONDecodeError, KeyError) as exc:
                    print(f"⚠ Skipping {filename}: {exc}")

        print(f"✅ Indexed {len(self.documents)} documents from {self.data_dir}")
        return self.documents

    # ------------------------------------------------------------------
    # Category indexers
    # ------------------------------------------------------------------

    def _index_champions(self, data: list[dict]) -> None:
        for champ in data:
            name = champ.get("name", "")
            champ_id = champ.get("champion_id", "")
            tags = champ.get("tags", [])
            stats = champ.get("stats", {})
            spells = champ.get("spells", [])
            passive = champ.get("passive", {})
            skins = champ.get("skins", [])

            # Build rich searchable content
            parts = [
                f"Champion: {name} ({champ_id})",
                f"Title: {champ.get('title', '')}",
                f"Tags/Roles: {_safe_join(tags)}",
                f"Resource: {champ.get('resource_type', '')}",
                f"Difficulty: {champ.get('difficulty', 0)}/10",
                f"Attack: {champ.get('attack', 0)} | Defense: {champ.get('defense', 0)} | Magic: {champ.get('magic', 0)}",
                "",
                "--- Stats ---",
                f"HP: {stats.get('hp', 0)} (+{stats.get('hp_per_level', 0)}/lv)",
                f"MP: {stats.get('mp', 0)} (+{stats.get('mp_per_level', 0)}/lv)",
                f"Armor: {stats.get('armor', 0)} (+{stats.get('armor_per_level', 0)}/lv)",
                f"MR: {stats.get('spell_block', 0)} (+{stats.get('spell_block_per_level', 0)}/lv)",
                f"AD: {stats.get('attack_damage', 0)} (+{stats.get('attack_damage_per_level', 0)}/lv)",
                f"AS: {stats.get('attack_speed', 0)} (+{stats.get('attack_speed_per_level', 0)}%/lv)",
                f"Move Speed: {stats.get('move_speed', 0)}",
                f"Attack Range: {stats.get('attack_range', 0)}",
            ]

            # Passive
            if passive:
                parts.append("")
                parts.append(f"Passive: {passive.get('name', '')} — {_strip_html(passive.get('description', ''))}")

            # Spells Q/W/E/R
            spell_keys = ["Q", "W", "E", "R"]
            for i, spell in enumerate(spells[:4]):
                key = spell_keys[i] if i < len(spell_keys) else f"Spell{i}"
                desc = _strip_html(spell.get("description", ""))
                cd = _safe_join(spell.get("cooldown", []))
                cost = _safe_join(spell.get("cost", []))
                parts.append(f"{key}: {spell.get('name', '')} — {desc}")
                parts.append(f"  Cooldown: {cd} | Cost: {cost}")

            # Skins
            if skins:
                skin_names = [s.get("name", "") for s in skins if s.get("name") != "default"]
                if skin_names:
                    parts.append(f"Skins: {_safe_join(skin_names)}")

            # Tips
            ally_tips = champ.get("ally_tips", [])
            enemy_tips = champ.get("enemy_tips", [])
            if ally_tips:
                parts.append(f"Ally Tips: {_safe_join(ally_tips, ' | ')}")
            if enemy_tips:
                parts.append(f"Enemy Tips: {_safe_join(enemy_tips, ' | ')}")

            # Lore
            lore = champ.get("lore", "")
            if lore:
                parts.append(f"Lore: {lore[:300]}")

            content = "\n".join(parts)
            keywords = [name.lower(), champ_id.lower()] + [t.lower() for t in tags]

            self.documents.append(Document(
                doc_id=f"champion_{champ_id}",
                category="champion",
                title=f"{name} — {champ.get('title', '')}",
                content=content,
                raw_data=champ,
                keywords=keywords,
            ))

    def _index_items(self, data: list[dict]) -> None:
        for item in data:
            name = item.get("name", "")
            item_id = item.get("item_id", "")
            gold = item.get("gold", {})
            desc = _strip_html(item.get("description", ""))
            plaintext = item.get("plaintext", "")
            tags = item.get("tags", [])
            stats = item.get("stats", {})
            from_items = item.get("from_items", [])
            into_items = item.get("into_items", [])

            # Build stat text
            stat_parts = []
            for stat_name, val in stats.items():
                if val != 0:
                    stat_parts.append(f"{stat_name}: {val}")

            parts = [
                f"Item: {name} (ID: {item_id})",
                f"Description: {desc}",
                f"Summary: {plaintext}",
                f"Tags: {_safe_join(tags)}",
                f"Gold — Base: {gold.get('base', 0)} | Total: {gold.get('total', 0)} | Sell: {gold.get('sell', 0)}",
            ]

            if stat_parts:
                parts.append(f"Stats: {_safe_join(stat_parts)}")
            if from_items:
                parts.append(f"Built from: {_safe_join(from_items)}")
            if into_items:
                parts.append(f"Builds into: {_safe_join(into_items)}")

            content = "\n".join(parts)
            keywords = [name.lower(), item_id] + [t.lower() for t in tags]

            self.documents.append(Document(
                doc_id=f"item_{item_id}",
                category="item",
                title=name,
                content=content,
                raw_data=item,
                keywords=keywords,
            ))

    def _index_runes(self, data: list[dict]) -> None:
        for path in data:
            path_name = path.get("name", "")
            runes = path.get("runes", [])

            rune_texts = []
            for rune in runes:
                desc = _strip_html(rune.get("long_desc", rune.get("short_desc", "")))
                rune_texts.append(f"  - {rune.get('name', '')} (Row {rune.get('row', 0)}): {desc}")

            content = f"Rune Path: {path_name}\n" + "\n".join(rune_texts)
            keywords = [path_name.lower()] + [r.get("name", "").lower() for r in runes]

            self.documents.append(Document(
                doc_id=f"rune_path_{path.get('path_id', '')}",
                category="rune",
                title=f"Rune Path: {path_name}",
                content=content,
                raw_data=path,
                keywords=keywords,
            ))

    def _index_spells(self, data: list[dict]) -> None:
        for spell in data:
            name = spell.get("name", "")
            desc = _strip_html(spell.get("description", ""))
            cd = _safe_join(spell.get("cooldown", []))
            modes = _safe_join(spell.get("modes", []))

            content = (
                f"Summoner Spell: {name}\n"
                f"Description: {desc}\n"
                f"Cooldown: {cd}\n"
                f"Summoner Level Required: {spell.get('summoner_level', 0)}\n"
                f"Game Modes: {modes}"
            )
            keywords = [name.lower(), spell.get("spell_id", "").lower()]

            self.documents.append(Document(
                doc_id=f"spell_{spell.get('spell_id', '')}",
                category="spell",
                title=f"Summoner Spell: {name}",
                content=content,
                raw_data=spell,
                keywords=keywords,
            ))

    def _index_maps(self, data: list[dict]) -> None:
        for m in data:
            content = f"Map: {m.get('name', '')} (ID: {m.get('map_id', '')})"
            self.documents.append(Document(
                doc_id=f"map_{m.get('map_id', '')}",
                category="map",
                title=m.get("name", ""),
                content=content,
                raw_data=m,
                keywords=[m.get("name", "").lower()],
            ))

    def _index_patches(self, data: list[dict]) -> None:
        # Group patches into a single summary document
        versions = [p.get("version", "") for p in data[:50]]  # Recent 50
        content = (
            f"Patch History — {len(data)} versions available\n"
            f"Latest: {versions[0] if versions else 'N/A'}\n"
            f"Recent patches: {_safe_join(versions[:20])}"
        )
        self.documents.append(Document(
            doc_id="patch_history",
            category="patch",
            title="Patch Version History",
            content=content,
            raw_data={"versions": [p.get("version", "") for p in data]},
            keywords=["patch", "version", "update", "cập nhật"],
        ))
