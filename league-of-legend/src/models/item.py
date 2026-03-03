"""Item data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItemGold:
    """Gold cost information for an item."""

    base: int = 0
    total: int = 0
    sell: int = 0
    purchasable: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ItemGold:
        return cls(
            base=data.get("base", 0),
            total=data.get("total", 0),
            sell=data.get("sell", 0),
            purchasable=data.get("purchasable", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "base": self.base,
            "total": self.total,
            "sell": self.sell,
            "purchasable": self.purchasable,
        }


@dataclass
class Item:
    """Full item data from Data Dragon."""

    item_id: str = ""
    name: str = ""
    description: str = ""
    plaintext: str = ""
    gold: ItemGold = field(default_factory=ItemGold)
    tags: list[str] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)
    from_items: list[str] = field(default_factory=list)
    into_items: list[str] = field(default_factory=list)
    maps: dict[str, bool] = field(default_factory=dict)
    depth: int = 0
    image_filename: str = ""
    required_champion: str = ""
    required_ally: str = ""
    in_store: bool = True

    @classmethod
    def from_dict(cls, item_id: str, data: dict[str, Any]) -> Item:
        return cls(
            item_id=item_id,
            name=data.get("name", ""),
            description=data.get("description", ""),
            plaintext=data.get("plaintext", ""),
            gold=ItemGold.from_dict(data.get("gold", {})),
            tags=data.get("tags", []),
            stats=data.get("stats", {}),
            from_items=data.get("from", []),
            into_items=data.get("into", []),
            maps={k: v for k, v in data.get("maps", {}).items()},
            depth=data.get("depth", 0),
            image_filename=data.get("image", {}).get("full", ""),
            required_champion=data.get("requiredChampion", ""),
            required_ally=data.get("requiredAlly", ""),
            in_store=data.get("inStore", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "plaintext": self.plaintext,
            "gold": self.gold.to_dict(),
            "tags": self.tags,
            "stats": self.stats,
            "from_items": self.from_items,
            "into_items": self.into_items,
            "maps": self.maps,
            "depth": self.depth,
            "image_filename": self.image_filename,
            "required_champion": self.required_champion,
            "required_ally": self.required_ally,
            "in_store": self.in_store,
        }
