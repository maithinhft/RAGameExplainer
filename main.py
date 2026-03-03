#!/usr/bin/env python3
"""
League of Legends RAG-powered Q&A — FastAPI Server
====================================================

Hệ thống hỏi đáp thông minh về League of Legends qua REST API.

Endpoints:
    POST /ask              — Hỏi đáp với RAG + LLM
    POST /search           — Chỉ tìm kiếm data (không gọi LLM)
    POST /ask-direct       — Gửi thẳng cho LLM (không RAG)
    GET  /stats            — Thống kê index
    GET  /health           — Health check

Chạy server:
    python main.py
    # hoặc
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import json
import os
import urllib.request
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag.pipeline import RAGPipeline


# ═══════════════════════════════════════════════════════════
# CẤU HÌNH
# ═══════════════════════════════════════════════════════════

# URL của Ollama LLM server
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://127.0.0.1:8080/nhan-tin-nhan")

# Tên mô hình LLM
MODEL_NAME = os.getenv("LLM_MODEL", "qwen3:14b")

# Đường dẫn tới dữ liệu đã crawl
DATA_DIR = os.getenv("DATA_DIR", "league-of-legend/data")

# Port mặc định
PORT = int(os.getenv("PORT", "8000"))


# ═══════════════════════════════════════════════════════════
# RAG PIPELINE (singleton, khởi tạo khi server start)
# ═══════════════════════════════════════════════════════════

pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo RAG pipeline khi server khởi động."""
    global pipeline
    print("🔧 Initializing RAG pipeline...")
    pipeline = RAGPipeline(
        data_dir=DATA_DIR,
        server_url=LLM_SERVER_URL,
        model_name=MODEL_NAME,
        top_k=5,
    )
    pipeline.initialize()
    print(f"✅ Server ready! Indexed {len(pipeline._indexer.documents)} documents")
    yield
    print("👋 Shutting down...")


# ═══════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="🎮 LoL RAG Q&A API",
    description=(
        "Hệ thống hỏi đáp thông minh về League of Legends sử dụng "
        "RAG (Retrieval-Augmented Generation) với dữ liệu từ Riot Data Dragon."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class AskRequest(BaseModel):
    """Body cho endpoint /ask và /ask-direct."""

    question: str = Field(..., description="Câu hỏi về League of Legends", min_length=1)
    top_k: int = Field(5, description="Số kết quả search context (1-20)", ge=1, le=20)
    compact: bool = Field(False, description="Dùng prompt ngắn gọn hơn")
    show_context: bool = Field(False, description="Trả về context tìm được")
    model: str | None = Field(None, description="Override tên mô hình LLM")
    server_url: str | None = Field(None, description="Override URL của LLM server")


class SearchRequest(BaseModel):
    """Body cho endpoint /search."""

    query: str = Field(..., description="Từ khóa tìm kiếm", min_length=1)
    top_k: int = Field(5, description="Số kết quả trả về (1-20)", ge=1, le=20)


class SearchResultItem(BaseModel):
    """Một kết quả tìm kiếm."""

    rank: int
    title: str
    category: str
    score: float
    match_type: str
    content: str


class AskResponse(BaseModel):
    """Response cho endpoint /ask."""

    question: str
    answer: str
    context: list[SearchResultItem] | None = None


class SearchResponse(BaseModel):
    """Response cho endpoint /search."""

    query: str
    results: list[SearchResultItem]
    total: int


class StatsResponse(BaseModel):
    """Response cho endpoint /stats."""

    total_documents: int
    categories: dict[str, int]
    llm_server_url: str
    model_name: str


# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check — kiểm tra server hoạt động."""
    return {
        "status": "ok",
        "pipeline_ready": pipeline is not None and pipeline.is_initialized,
    }


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Thống kê dữ liệu đã index."""
    if not pipeline or not pipeline._indexer:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")

    # Đếm theo category
    categories: dict[str, int] = {}
    for doc in pipeline._indexer.documents:
        categories[doc.category] = categories.get(doc.category, 0) + 1

    return StatsResponse(
        total_documents=len(pipeline._indexer.documents),
        categories=categories,
        llm_server_url=pipeline.server_url,
        model_name=pipeline.model_name,
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Tìm kiếm dữ liệu game — không gọi LLM.

    Trả về danh sách documents liên quan đến query.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")

    results = pipeline.search(request.query)
    items = [
        SearchResultItem(
            rank=i,
            title=r.document.title,
            category=r.document.category,
            score=round(r.score, 3),
            match_type=r.match_type,
            content=r.document.content[:500],
        )
        for i, r in enumerate(results[:request.top_k], 1)
    ]

    return SearchResponse(
        query=request.query,
        results=items,
        total=len(items),
    )


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Hỏi đáp với RAG — tìm context từ data rồi gửi cho LLM.

    Flow: question → search relevant data → build prompt with context → LLM → answer
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")

    # Override settings nếu cần
    original_top_k = pipeline.top_k
    original_compact = pipeline.compact_mode
    original_model = pipeline.model_name
    original_url = pipeline.server_url

    try:
        pipeline.top_k = request.top_k
        pipeline.compact_mode = request.compact
        if request.model:
            pipeline.model_name = request.model
        if request.server_url:
            pipeline.server_url = request.server_url

        # Lấy context
        context_items = None
        if request.show_context:
            search_results = pipeline.search(request.question)
            context_items = [
                SearchResultItem(
                    rank=i,
                    title=r.document.title,
                    category=r.document.category,
                    score=round(r.score, 3),
                    match_type=r.match_type,
                    content=r.document.content[:500],
                )
                for i, r in enumerate(search_results, 1)
            ]

        # Gọi RAG pipeline
        answer = pipeline.ask(request.question, show_context=False)

        return AskResponse(
            question=request.question,
            answer=answer,
            context=context_items,
        )

    except ConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Không thể kết nối đến LLM server: {exc}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Restore settings
        pipeline.top_k = original_top_k
        pipeline.compact_mode = original_compact
        pipeline.model_name = original_model
        pipeline.server_url = original_url


@app.post("/ask-direct", response_model=AskResponse)
async def ask_direct(request: AskRequest):
    """Hỏi thẳng LLM mà KHÔNG có RAG context.

    Gửi câu hỏi trực tiếp đến Ollama server.
    """
    server_url = request.server_url or LLM_SERVER_URL
    model = request.model or MODEL_NAME

    payload = {
        "ten_mo_hinh": model,
        "cau_hoi": request.question,
    }

    req = urllib.request.Request(
        server_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
    )

    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode("utf-8"))
        answer = result.get("cau_tra_loi_tu_he_thong", "(Không có câu trả lời)")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM server error: {exc}")

    return AskResponse(question=request.question, answer=answer)


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"� Starting LoL RAG API server on http://0.0.0.0:{PORT}")
    print(f"📖 Docs: http://localhost:{PORT}/docs")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
    )