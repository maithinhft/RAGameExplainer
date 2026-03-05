"""
Response Cache — LRU cache with TTL and semantic similarity matching.

Caches LLM responses to avoid redundant calls for identical/similar questions.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class CacheEntry:
    """A cached response with metadata."""

    question: str
    answer: str
    cache_key: str
    created_at: float
    hit_count: int = 0


class ResponseCache:
    """LRU cache with TTL and semantic similarity for LLM responses.

    Usage::

        cache = ResponseCache(max_size=200, ttl=3600)
        cache.put("Ahri build?", "context_hash", "Ahri nên lên...")
        result = cache.get("Ahri build?", "context_hash")  # Cache hit
        result = cache.get("Build Ahri?", "context_hash")   # Semantic hit
    """

    def __init__(
        self,
        max_size: int = 200,
        ttl: int = 3600,
        similarity_threshold: float = 0.85,
    ) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # Stats
        self.total_hits = 0
        self.total_misses = 0
        self.semantic_hits = 0

    def _make_key(self, question: str, context_hash: str = "") -> str:
        """Generate cache key from question + context."""
        normalized = question.strip().lower()
        raw = f"{normalized}|{context_hash}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, question: str, context_hash: str = "") -> str | None:
        """Look up a cached response.

        1. Try exact cache key match
        2. Try semantic similarity match (>85% similar questions)

        Returns cached answer or None.
        """
        with self._lock:
            self._evict_expired()

            # 1. Exact match
            key = self._make_key(question, context_hash)
            if key in self._cache:
                entry = self._cache[key]
                entry.hit_count += 1
                self.total_hits += 1
                self._cache.move_to_end(key)  # LRU update
                return entry.answer

            # 2. Semantic match
            normalized = question.strip().lower()
            for cached_key, entry in self._cache.items():
                ratio = SequenceMatcher(
                    None, normalized, entry.question.strip().lower()
                ).ratio()
                if ratio >= self.similarity_threshold:
                    entry.hit_count += 1
                    self.total_hits += 1
                    self.semantic_hits += 1
                    self._cache.move_to_end(cached_key)
                    return entry.answer

            self.total_misses += 1
            return None

    def put(self, question: str, context_hash: str, answer: str) -> None:
        """Store a response in the cache."""
        with self._lock:
            key = self._make_key(question, context_hash)

            if key in self._cache:
                # Update existing
                self._cache[key].answer = answer
                self._cache[key].created_at = time.time()
                self._cache.move_to_end(key)
            else:
                # Evict LRU if full
                while len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)

                self._cache[key] = CacheEntry(
                    question=question,
                    answer=answer,
                    cache_key=key,
                    created_at=time.time(),
                )

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self.total_hits = 0
            self.total_misses = 0
            self.semantic_hits = 0

    def _evict_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now - v.created_at > self.ttl
        ]
        for k in expired:
            del self._cache[k]

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self.total_hits + self.total_misses
        hit_rate = (self.total_hits / total * 100) if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "total_requests": total,
            "hits": self.total_hits,
            "misses": self.total_misses,
            "semantic_hits": self.semantic_hits,
            "hit_rate_percent": round(hit_rate, 1),
        }
