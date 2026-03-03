"""
Search Engine — Hybrid TF-IDF + keyword search over indexed LoL documents.

Combines:
1. TF-IDF cosine similarity (semantic-like matching)
2. Exact keyword matching (champion/item names)
3. Fuzzy matching (handles typos and Vietnamese terms)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag.indexer import Document, Indexer


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    document: Document
    score: float
    match_type: str  # "tfidf", "keyword", "fuzzy", "combined"

    def __repr__(self) -> str:
        return f"SearchResult({self.document.title}, score={self.score:.3f}, type={self.match_type})"


# Vietnamese → English alias mapping for common LoL terms
TERM_ALIASES: dict[str, list[str]] = {
    # Items (Vietnamese → English)
    "đai lưng hextech": ["hextech rocketbelt", "rocketbelt"],
    "giày": ["boots"],
    "giáp gai": ["thornmail"],
    "mũ phù thủy": ["rabadon", "deathcap", "rabadon's deathcap"],
    "gươm vô cực": ["infinity edge"],
    "kiếm vô danh": ["blade of the ruined king", "botrk"],
    "sách thần": ["mejai", "mejai's soulstealer"],
    "cung longbow": ["rapid firecannon"],
    "đĩa hextech": ["hextech alternator"],
    "mặt nạ hư vô": ["void staff"],
    "nanh nashor": ["nashor's tooth"],
    "giày pháp sư": ["sorcerer's shoes"],
    "giày thủy ngân": ["mercury's treads"],
    "áo giáp hỏa giáp": ["sunfire aegis", "sunfire cape"],
    "cây trượng thiên thần": ["archangel's staff"],
    "hồng ngọc": ["ruby crystal"],
    # Runes
    "điện hình": ["electrocute"],
    "chinh phục": ["conqueror"],
    "bước chân nhanh": ["fleet footwork"],
    "đánh dấu": ["press the attack"],
    # Roles
    "xạ thủ": ["marksman", "adc"],
    "pháp sư": ["mage"],
    "sát thủ": ["assassin"],
    "đấu sĩ": ["fighter"],
    "hỗ trợ": ["support"],
    "đỡ đòn": ["tank"],
    # General terms
    "tướng": ["champion"],
    "trang bị": ["item"],
    "bảng ngọc": ["rune"],
    "phép bổ trợ": ["summoner spell"],
    "bản cập nhật": ["patch", "update"],
    "tốc biến": ["flash"],
    "thiêu đốt": ["ignite"],
    "hồi máu": ["heal"],
    "tàng hình": ["stealth", "invisibility"],
}


class SearchEngine:
    """Hybrid search engine combining TF-IDF, keyword, and fuzzy matching.

    Usage::

        indexer = Indexer()
        indexer.build()
        engine = SearchEngine(indexer)
        results = engine.search("Ahri hextech rocketbelt", top_k=5)
    """

    def __init__(self, indexer: Indexer) -> None:
        self.indexer = indexer
        self.documents = indexer.documents

        # Build TF-IDF index
        corpus = [doc.content for doc in self.documents]
        self._vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            stop_words=None,  # Keep all terms for game data
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for documents matching the query.

        Args:
            query: User question in Vietnamese or English.
            top_k: Number of results to return.

        Returns:
            List of SearchResults sorted by relevance score (highest first).
        """
        # Expand query with aliases
        expanded_query = self._expand_query(query)

        # 1. TF-IDF search
        tfidf_results = self._tfidf_search(expanded_query, top_k=top_k * 2)

        # 2. Keyword search
        keyword_results = self._keyword_search(query, top_k=top_k)

        # 3. Fuzzy search
        fuzzy_results = self._fuzzy_search(query, top_k=top_k)

        # Merge and deduplicate
        merged = self._merge_results(tfidf_results, keyword_results, fuzzy_results, top_k=top_k)

        return merged

    def _expand_query(self, query: str) -> str:
        """Expand Vietnamese terms in query to English equivalents."""
        expanded = query.lower()
        for vn_term, en_terms in TERM_ALIASES.items():
            if vn_term in expanded:
                expanded += " " + " ".join(en_terms)
        return expanded

    def _tfidf_search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """TF-IDF cosine similarity search."""
        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top indices
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.01:  # Minimum threshold
                results.append(SearchResult(
                    document=self.documents[idx],
                    score=score,
                    match_type="tfidf",
                ))
        return results

    def _keyword_search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Exact keyword matching against document keywords and titles."""
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))

        results = []
        for doc in self.documents:
            score = 0.0

            # Check keywords
            for kw in doc.keywords:
                if kw in query_lower:
                    score += 1.0
                elif any(term in kw for term in query_terms):
                    score += 0.5

            # Check title
            title_lower = doc.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 0.8

            if score > 0:
                results.append(SearchResult(
                    document=doc,
                    score=min(score, 3.0),  # Cap at 3.0
                    match_type="keyword",
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _fuzzy_search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Fuzzy matching for handling typos and partial matches."""
        query_lower = query.lower()
        query_terms = re.findall(r'\w{3,}', query_lower)  # Words with 3+ chars

        results = []
        for doc in self.documents:
            best_ratio = 0.0
            for term in query_terms:
                for kw in doc.keywords:
                    ratio = SequenceMatcher(None, term, kw).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio

                # Also check against title words
                title_words = re.findall(r'\w+', doc.title.lower())
                for tw in title_words:
                    ratio = SequenceMatcher(None, term, tw).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio

            if best_ratio > 0.6:  # Minimum fuzzy threshold
                results.append(SearchResult(
                    document=doc,
                    score=best_ratio,
                    match_type="fuzzy",
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _merge_results(
        self,
        tfidf: list[SearchResult],
        keyword: list[SearchResult],
        fuzzy: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Merge results from all search methods, boosting documents found by multiple methods."""
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}
        match_types: dict[str, set[str]] = {}

        # Weights for each method
        weights = {"tfidf": 1.0, "keyword": 1.5, "fuzzy": 0.5}

        for result_set in [tfidf, keyword, fuzzy]:
            for result in result_set:
                doc_id = result.document.doc_id
                weight = weights.get(result.match_type, 1.0)
                weighted_score = result.score * weight

                if doc_id not in scores:
                    scores[doc_id] = 0.0
                    doc_map[doc_id] = result.document
                    match_types[doc_id] = set()

                scores[doc_id] += weighted_score
                match_types[doc_id].add(result.match_type)

        # Boost documents found by multiple methods
        for doc_id in scores:
            if len(match_types[doc_id]) >= 2:
                scores[doc_id] *= 1.3
            if len(match_types[doc_id]) >= 3:
                scores[doc_id] *= 1.5

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            results.append(SearchResult(
                document=doc_map[doc_id],
                score=scores[doc_id],
                match_type="combined" if len(match_types[doc_id]) > 1 else match_types[doc_id].pop(),
            ))

        return results
