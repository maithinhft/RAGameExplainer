"""Summoner Spell data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SummonerSpell:
    """Data for a single summoner spell (Flash, Ignite, etc.)."""

    spell_id: str = ""
    key: int = 0
    name: str = ""
    description: str = ""
    tooltip: str = ""
    cooldown: list[float] = field(default_factory=list)
    cost: list[float] = field(default_factory=list)
    range: list[float] = field(default_factory=list)
    summoner_level: int = 0
    modes: list[str] = field(default_factory=list)
    image_filename: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SummonerSpell:
        return cls(
            spell_id=data.get("id", ""),
            key=int(data.get("key", 0)),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tooltip=data.get("tooltip", ""),
            cooldown=data.get("cooldown", []),
            cost=data.get("cost", []),
            range=data.get("range", []),
            summoner_level=data.get("summonerLevel", 0),
            modes=data.get("modes", []),
            image_filename=data.get("image", {}).get("full", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "spell_id": self.spell_id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "tooltip": self.tooltip,
            "cooldown": self.cooldown,
            "cost": self.cost,
            "range": self.range,
            "summoner_level": self.summoner_level,
            "modes": self.modes,
            "image_filename": self.image_filename,
        }
