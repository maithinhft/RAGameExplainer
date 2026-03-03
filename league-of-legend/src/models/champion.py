"""Champion data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChampionStats:
    """Base and per-level stats for a champion."""

    hp: float = 0
    hp_per_level: float = 0
    mp: float = 0
    mp_per_level: float = 0
    move_speed: float = 0
    armor: float = 0
    armor_per_level: float = 0
    spell_block: float = 0
    spell_block_per_level: float = 0
    attack_range: float = 0
    hp_regen: float = 0
    hp_regen_per_level: float = 0
    mp_regen: float = 0
    mp_regen_per_level: float = 0
    crit: float = 0
    crit_per_level: float = 0
    attack_damage: float = 0
    attack_damage_per_level: float = 0
    attack_speed_per_level: float = 0
    attack_speed: float = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChampionStats:
        return cls(
            hp=data.get("hp", 0),
            hp_per_level=data.get("hpperlevel", 0),
            mp=data.get("mp", 0),
            mp_per_level=data.get("mpperlevel", 0),
            move_speed=data.get("movespeed", 0),
            armor=data.get("armor", 0),
            armor_per_level=data.get("armorperlevel", 0),
            spell_block=data.get("spellblock", 0),
            spell_block_per_level=data.get("spellblockperlevel", 0),
            attack_range=data.get("attackrange", 0),
            hp_regen=data.get("hpregen", 0),
            hp_regen_per_level=data.get("hpregenperlevel", 0),
            mp_regen=data.get("mpregen", 0),
            mp_regen_per_level=data.get("mpregenperlevel", 0),
            crit=data.get("crit", 0),
            crit_per_level=data.get("critperlevel", 0),
            attack_damage=data.get("attackdamage", 0),
            attack_damage_per_level=data.get("attackdamageperlevel", 0),
            attack_speed_per_level=data.get("attackspeedperlevel", 0),
            attack_speed=data.get("attackspeed", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hp": self.hp,
            "hp_per_level": self.hp_per_level,
            "mp": self.mp,
            "mp_per_level": self.mp_per_level,
            "move_speed": self.move_speed,
            "armor": self.armor,
            "armor_per_level": self.armor_per_level,
            "spell_block": self.spell_block,
            "spell_block_per_level": self.spell_block_per_level,
            "attack_range": self.attack_range,
            "hp_regen": self.hp_regen,
            "hp_regen_per_level": self.hp_regen_per_level,
            "mp_regen": self.mp_regen,
            "mp_regen_per_level": self.mp_regen_per_level,
            "crit": self.crit,
            "crit_per_level": self.crit_per_level,
            "attack_damage": self.attack_damage,
            "attack_damage_per_level": self.attack_damage_per_level,
            "attack_speed_per_level": self.attack_speed_per_level,
            "attack_speed": self.attack_speed,
        }


@dataclass
class ChampionSpell:
    """A single champion ability (Q/W/E/R) or passive."""

    spell_id: str = ""
    name: str = ""
    description: str = ""
    tooltip: str = ""
    cooldown: list[float] = field(default_factory=list)
    cost: list[float] = field(default_factory=list)
    range: list[float] = field(default_factory=list)
    max_rank: int = 0
    image_filename: str = ""
    resource: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChampionSpell:
        return cls(
            spell_id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tooltip=data.get("tooltip", ""),
            cooldown=data.get("cooldown", []),
            cost=data.get("cost", []),
            range=data.get("range", []),
            max_rank=data.get("maxrank", 0),
            image_filename=data.get("image", {}).get("full", ""),
            resource=data.get("resource", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "spell_id": self.spell_id,
            "name": self.name,
            "description": self.description,
            "tooltip": self.tooltip,
            "cooldown": self.cooldown,
            "cost": self.cost,
            "range": self.range,
            "max_rank": self.max_rank,
            "image_filename": self.image_filename,
            "resource": self.resource,
        }


@dataclass
class ChampionSkin:
    """A champion skin entry."""

    skin_id: int = 0
    num: int = 0
    name: str = ""
    chromas: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChampionSkin:
        return cls(
            skin_id=int(data.get("id", 0)),
            num=data.get("num", 0),
            name=data.get("name", ""),
            chromas=data.get("chromas", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skin_id": self.skin_id,
            "num": self.num,
            "name": self.name,
            "chromas": self.chromas,
        }


@dataclass
class Champion:
    """Full champion data from Data Dragon."""

    champion_id: str = ""
    key: int = 0
    name: str = ""
    title: str = ""
    blurb: str = ""
    lore: str = ""
    tags: list[str] = field(default_factory=list)
    resource_type: str = ""
    difficulty: int = 0
    attack: int = 0
    defense: int = 0
    magic: int = 0
    stats: ChampionStats = field(default_factory=ChampionStats)
    spells: list[ChampionSpell] = field(default_factory=list)
    passive: ChampionSpell | None = None
    skins: list[ChampionSkin] = field(default_factory=list)
    ally_tips: list[str] = field(default_factory=list)
    enemy_tips: list[str] = field(default_factory=list)
    image_filename: str = ""
    version: str = ""

    @classmethod
    def from_list_data(cls, data: dict[str, Any]) -> Champion:
        """Create from the champion list endpoint (partial data)."""
        info = data.get("info", {})
        return cls(
            champion_id=data.get("id", ""),
            key=int(data.get("key", 0)),
            name=data.get("name", ""),
            title=data.get("title", ""),
            blurb=data.get("blurb", ""),
            tags=data.get("tags", []),
            resource_type=data.get("partype", ""),
            difficulty=info.get("difficulty", 0),
            attack=info.get("attack", 0),
            defense=info.get("defense", 0),
            magic=info.get("magic", 0),
            stats=ChampionStats.from_dict(data.get("stats", {})),
            image_filename=data.get("image", {}).get("full", ""),
            version=data.get("version", ""),
        )

    @classmethod
    def from_detail_data(cls, data: dict[str, Any]) -> Champion:
        """Create from the champion detail endpoint (full data)."""
        info = data.get("info", {})
        passive_data = data.get("passive", {})
        passive = ChampionSpell(
            spell_id="passive",
            name=passive_data.get("name", ""),
            description=passive_data.get("description", ""),
            image_filename=passive_data.get("image", {}).get("full", ""),
        ) if passive_data else None

        return cls(
            champion_id=data.get("id", ""),
            key=int(data.get("key", 0)),
            name=data.get("name", ""),
            title=data.get("title", ""),
            blurb=data.get("blurb", ""),
            lore=data.get("lore", ""),
            tags=data.get("tags", []),
            resource_type=data.get("partype", ""),
            difficulty=info.get("difficulty", 0),
            attack=info.get("attack", 0),
            defense=info.get("defense", 0),
            magic=info.get("magic", 0),
            stats=ChampionStats.from_dict(data.get("stats", {})),
            spells=[ChampionSpell.from_dict(s) for s in data.get("spells", [])],
            passive=passive,
            skins=[ChampionSkin.from_dict(s) for s in data.get("skins", [])],
            ally_tips=data.get("allytips", []),
            enemy_tips=data.get("enemytips", []),
            image_filename=data.get("image", {}).get("full", ""),
            version=data.get("version", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "champion_id": self.champion_id,
            "key": self.key,
            "name": self.name,
            "title": self.title,
            "blurb": self.blurb,
            "lore": self.lore,
            "tags": self.tags,
            "resource_type": self.resource_type,
            "difficulty": self.difficulty,
            "attack": self.attack,
            "defense": self.defense,
            "magic": self.magic,
            "stats": self.stats.to_dict(),
            "spells": [s.to_dict() for s in self.spells],
            "passive": self.passive.to_dict() if self.passive else None,
            "skins": [s.to_dict() for s in self.skins],
            "ally_tips": self.ally_tips,
            "enemy_tips": self.enemy_tips,
            "image_filename": self.image_filename,
            "version": self.version,
        }
