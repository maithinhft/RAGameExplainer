"""
RAG Pipeline — Orchestrates the full Retrieval-Augmented Generation flow.

    question → search → build prompt → query LLM → answer
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from rag.indexer import Indexer
from rag.search import SearchEngine, SearchResult
from rag.prompt_builder import build_prompt, build_prompt_compact


class RAGPipeline:
    """End-to-end RAG pipeline for League of Legends questions.

    Usage::

        pipeline = RAGPipeline(
            data_dir="league-of-legend/data",
            server_url="https://xxxx.ngrok-free.app/nhan-tin-nhan",
            model_name="qwen3.5:9b",
        )
        pipeline.initialize()
        answer = pipeline.ask("Tại sao lên đai lưng hextech cho Ahri?")
    """

    def __init__(
        self,
        data_dir: str | Path = "league-of-legend/data",
        server_url: str = "",
        model_name: str = "qwen3.5:9b",
        top_k: int = 5,
        compact_mode: bool = False,
        max_context_length: int = 4000,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.server_url = server_url
        self.model_name = model_name
        self.top_k = top_k
        self.compact_mode = compact_mode
        self.max_context_length = max_context_length

        self._indexer: Indexer | None = None
        self._engine: SearchEngine | None = None

    def initialize(self) -> None:
        """Build the index and search engine. Call once before asking questions."""
        print("🔧 Initializing RAG pipeline...")
        self._indexer = Indexer(data_dir=self.data_dir)
        self._indexer.build()
        self._engine = SearchEngine(self._indexer)
        print("✅ RAG pipeline ready!\n")

    @property
    def is_initialized(self) -> bool:
        return self._engine is not None

    def search(self, question: str) -> list[SearchResult]:
        """Search for relevant documents without querying the LLM."""
        if not self._engine:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")
        return self._engine.search(question, top_k=self.top_k)

    def build_augmented_prompt(self, question: str) -> str:
        """Build a context-augmented prompt for the given question."""
        results = self.search(question)

        if self.compact_mode:
            return build_prompt_compact(question, results, self.max_context_length)
        return build_prompt(question, results, self.max_context_length)

    def ask(self, question: str, show_context: bool = False) -> str:
        """Full pipeline: search → build prompt → query LLM → return answer.

        Args:
            question: The user's question in Vietnamese or English.
            show_context: If True, print the retrieved context before querying.

        Returns:
            The LLM's answer string.
        """
        if not self.is_initialized:
            self.initialize()

        # Step 1: Search for relevant documents
        results = self.search(question)

        if show_context:
            print("\n📚 Retrieved context:")
            for i, r in enumerate(results, 1):
                print(f"  [{i}] {r.document.title} (score: {r.score:.3f}, type: {r.match_type})")
            print()

        # Step 2: Build augmented prompt
        if self.compact_mode:
            prompt = build_prompt_compact(question, results, self.max_context_length)
        else:
            prompt = build_prompt(question, results, self.max_context_length)

        # Step 3: Query LLM
        answer = self._query_llm(prompt)

        return answer

    def _query_llm(self, prompt: str) -> str:
        """Send the augmented prompt to the Ollama server via ngrok.

        Args:
            prompt: The full prompt including system instructions and context.

        Returns:
            The LLM's response text.

        Raises:
            ConnectionError: If the server is unreachable.
        """
        if not self.server_url:
            raise ValueError(
                "Server URL not configured. Set server_url when creating RAGPipeline."
            )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }

        req = urllib.request.Request(
            self.server_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

        try:
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "(Không có câu trả lời)")
        except Exception as exc:
            raise ConnectionError(f"Failed to reach LLM server: {exc}") from exc

    def ask_offline(self, question: str) -> str:
        """Search-only mode: return relevant data without querying the LLM.

        Useful when the Ollama server is not running.
        """
        if not self.is_initialized:
            self.initialize()

        results = self.search(question)

        if not results:
            return "Không tìm thấy dữ liệu liên quan."

        parts = [f"🔍 Tìm thấy {len(results)} kết quả liên quan:\n"]
        for i, r in enumerate(results, 1):
            parts.append(
                f"{'─' * 50}\n"
                f"[{i}] {r.document.title}\n"
                f"    Category: {r.document.category} | Score: {r.score:.3f}\n"
                f"    {r.document.content[:500]}\n"
            )

        return "\n".join(parts)
