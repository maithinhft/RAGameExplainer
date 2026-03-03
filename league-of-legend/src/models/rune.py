"""Rune (Runes Reforged) data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Rune:
    """A single rune within a rune path."""

    rune_id: int = 0
    key: str = ""
    name: str = ""
    short_desc: str = ""
    long_desc: str = ""
    icon: str = ""
    row: int = 0
    slot: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any], row: int = 0, slot: int = 0) -> Rune:
        return cls(
            rune_id=data.get("id", 0),
            key=data.get("key", ""),
            name=data.get("name", ""),
            short_desc=data.get("shortDesc", ""),
            long_desc=data.get("longDesc", ""),
            icon=data.get("icon", ""),
            row=row,
            slot=slot,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rune_id": self.rune_id,
            "key": self.key,
            "name": self.name,
            "short_desc": self.short_desc,
            "long_desc": self.long_desc,
            "icon": self.icon,
            "row": self.row,
            "slot": self.slot,
        }


@dataclass
class RunePath:
    """A rune path (e.g. Precision, Domination) containing multiple rune slots."""

    path_id: int = 0
    key: str = ""
    name: str = ""
    icon: str = ""
    runes: list[Rune] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunePath:
        runes: list[Rune] = []
        for row_idx, slot_list in enumerate(data.get("slots", [])):
            for slot_idx, rune_data in enumerate(slot_list.get("runes", [])):
                runes.append(Rune.from_dict(rune_data, row=row_idx, slot=slot_idx))

        return cls(
            path_id=data.get("id", 0),
            key=data.get("key", ""),
            name=data.get("name", ""),
            icon=data.get("icon", ""),
            runes=runes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "key": self.key,
            "name": self.name,
            "icon": self.icon,
            "runes": [r.to_dict() for r in self.runes],
        }
