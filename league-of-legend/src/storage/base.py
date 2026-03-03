"""Abstract storage interface."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class BaseStorage(abc.ABC):
    """Interface for persisting crawled data."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    async def save(self, category: str, data: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> None:
        """Persist a list of serialized model dicts under *category*."""
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...
