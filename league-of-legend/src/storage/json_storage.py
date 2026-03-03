"""JSON file storage backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.storage.base import BaseStorage
from src.utils import get_logger

logger = get_logger("storage.json")


class JsonStorage(BaseStorage):
    """Save crawled data as pretty-printed JSON files.

    Output structure::

        data/
        ├── champions.json          # Full list
        ├── champions/              # Individual files
        │   ├── Aatrox.json
        │   ├── Ahri.json
        │   └── ...
        ├── items.json
        ├── runes.json
        ├── spells.json
        ├── maps.json
        ├── patches.json
        └── metadata.json           # Crawl metadata
    """

    async def save(
        self,
        category: str,
        data: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Save aggregate file
        agg_path = self.output_dir / f"{category}.json"
        payload = {
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "count": len(data),
            "data": data,
        }
        if metadata:
            payload["metadata"] = metadata

        agg_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved [bold]%d[/] %s → %s", len(data), category, agg_path)

        # Save individual files for champions (keyed by champion_id or name)
        if category == "champions" and data:
            individual_dir = self.output_dir / category
            individual_dir.mkdir(parents=True, exist_ok=True)
            for item in data:
                name = item.get("champion_id") or item.get("name", "unknown")
                file_path = individual_dir / f"{name}.json"
                file_path.write_text(
                    json.dumps(item, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            logger.info("Saved %d individual champion files → %s/", len(data), individual_dir)

    async def close(self) -> None:
        pass  # No resources to clean up for JSON
