"""Patch / version data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PatchVersion:
    """Represents a game patch version."""

    version: str = ""
    major: int = 0
    minor: int = 0
    patch: int = 0

    @classmethod
    def from_string(cls, version_str: str) -> PatchVersion:
        """Parse a version string like '16.4.1' into components."""
        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        return cls(version=version_str, major=major, minor=minor, patch=patch)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
        }

    def __str__(self) -> str:
        return self.version
