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

import asyncio
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.pipeline import RAGPipeline
from rag.queue import RequestQueue


# ═══════════════════════════════════════════════════════════
# CẤU HÌNH
# ═══════════════════════════════════════════════════════════

# URL của Ollama LLM server (local)
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://127.0.0.1:11434/api/generate")

# Tên mô hình LLM
MODEL_NAME = os.getenv("LLM_MODEL", "qwen3.5:9b")

# Đường dẫn tới dữ liệu đã crawl
DATA_DIR = os.getenv("DATA_DIR", "league-of-legend/data")

# Thư mục gốc của crawler
CRAWLER_DIR = os.getenv("CRAWLER_DIR", "league-of-legend")

# Chu kỳ cập nhật dữ liệu (giây) — mặc định 1 tiếng
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL_SECONDS", str(60 * 60)))

# Port mặc định
PORT = int(os.getenv("PORT", "8000"))


# ═══════════════════════════════════════════════════════════
# RAG PIPELINE (singleton, khởi tạo khi server start)
# ═══════════════════════════════════════════════════════════

pipeline: RAGPipeline | None = None
llm_queue: RequestQueue = RequestQueue(max_concurrent=1, timeout=120)
_refresh_task: asyncio.Task | None = None
last_refresh_time: str = "(chưa cập nhật)"


def _run_crawler() -> bool:
    """Chạy crawler để lấy dữ liệu mới. Trả về True nếu thành công."""
    data_path = Path(DATA_DIR)

    # Bước 1: Xóa toàn bộ dữ liệu cũ
    if data_path.exists():
        print("🗑️  Xóa dữ liệu cũ...")
        shutil.rmtree(data_path)

    # Bước 2: Chạy crawler
    print("🔄 Đang crawl dữ liệu mới từ Data Dragon...")
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--all", "--lang", "vi_VN"],
            cwd=CRAWLER_DIR,
            capture_output=True,
            text=True,
            timeout=300,  # timeout 5 phút
        )
        if result.returncode == 0:
            print("✅ Crawl dữ liệu thành công!")
            return True
        else:
            print(f"❌ Crawl thất bại (exit code {result.returncode})")
            print(f"   stderr: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Crawl bị timeout (> 5 phút)")
        return False
    except Exception as exc:
        print(f"❌ Lỗi khi chạy crawler: {exc}")
        return False


def _rebuild_pipeline() -> None:
    """Khởi tạo lại RAG pipeline với dữ liệu mới."""
    global pipeline, last_refresh_time
    print("🔧 Rebuilding RAG pipeline...")
    pipeline = RAGPipeline(
        data_dir=DATA_DIR,
        server_url=LLM_SERVER_URL,
        model_name=MODEL_NAME,
        top_k=5,
    )
    pipeline.initialize()
    last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"✅ Pipeline rebuilt! {len(pipeline._indexer.documents)} documents indexed at {last_refresh_time}")


async def _periodic_refresh() -> None:
    """Background task: định kỳ crawl lại dữ liệu và rebuild index."""
    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        print(f"\n{'='*60}")
        print(f"⏰ Bắt đầu cập nhật dữ liệu định kỳ ({REFRESH_INTERVAL}s interval)...")
        print(f"{'='*60}")

        # Chạy crawler trong thread pool để không block event loop
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, _run_crawler)

        if success:
            await loop.run_in_executor(None, _rebuild_pipeline)
        else:
            print("⚠️  Giữ nguyên dữ liệu cũ do crawl thất bại.")

        print(f"{'='*60}\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo RAG pipeline khi server khởi động + bật scheduler."""
    global pipeline, _refresh_task

    # Crawl dữ liệu ngay lần đầu khi start
    print("🚀 First start — crawling fresh data...")
    success = _run_crawler()
    if not success:
        print("⚠️  Crawl lần đầu thất bại, thử dùng dữ liệu cũ nếu có...")
    _rebuild_pipeline()

    # Bật background task cập nhật định kỳ
    _refresh_task = asyncio.create_task(_periodic_refresh())
    interval_min = REFRESH_INTERVAL // 60
    print(f"⏰ Auto-refresh enabled: mỗi {interval_min} phút")

    yield

    # Cleanup
    if _refresh_task:
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass
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
    last_refresh: str
    refresh_interval_minutes: int


# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check — kiểm tra server hoạt động."""
    return {
        "status": "ok",
        "pipeline_ready": pipeline is not None and pipeline.is_initialized,
        "last_refresh": last_refresh_time,
    }


@app.post("/refresh")
async def manual_refresh():
    """Cập nhật dữ liệu thủ công — xóa data cũ và crawl lại."""
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _run_crawler)
    if success:
        await loop.run_in_executor(None, _rebuild_pipeline)
        return {"status": "ok", "message": "Dữ liệu đã được cập nhật", "last_refresh": last_refresh_time}
    raise HTTPException(status_code=500, detail="Crawl thất bại, giữ lại dữ liệu cũ")


@app.get("/cache-stats")
async def cache_stats():
    """Thống kê cache và queue."""
    return {
        "cache": pipeline.cache.stats if pipeline else {},
        "queue": llm_queue.stats.to_dict(),
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
        last_refresh=last_refresh_time,
        refresh_interval_minutes=REFRESH_INTERVAL // 60,
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


@app.get("/champions")
async def list_champions():
    """Danh sách tất cả tướng — cho frontend champion selector."""
    if not pipeline or not pipeline._indexer:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")

    champions = []
    for doc in pipeline._indexer.documents:
        if doc.category == "champion":
            raw = doc.raw_data
            champions.append({
                "id": raw.get("champion_id", ""),
                "name": raw.get("name", ""),
                "title": raw.get("title", ""),
                "tags": raw.get("tags", []),
                "image": f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/{raw.get('champion_id', '')}.png",
            })

    champions.sort(key=lambda c: c["name"])
    return {"champions": champions, "total": len(champions)}


@app.get("/items")
async def list_items():
    """Danh sách tất cả trang bị — cho frontend item builder."""
    if not pipeline or not pipeline._indexer:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng")

    items_list = []
    for doc in pipeline._indexer.documents:
        if doc.category == "item":
            raw = doc.raw_data
            gold = raw.get("gold", {})
            # Chỉ lấy item có thể mua (purchasable)
            if not gold.get("purchasable", True):
                continue
            items_list.append({
                "id": raw.get("item_id", ""),
                "name": raw.get("name", ""),
                "description": raw.get("plaintext", ""),
                "gold": gold.get("total", 0),
                "tags": raw.get("tags", []),
                "image": f"https://ddragon.leagueoflegends.com/cdn/14.24.1/img/item/{raw.get('item_id', '')}.png",
            })

    items_list.sort(key=lambda i: i["name"])
    return {"items": items_list, "total": len(items_list)}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Hỏi đáp với RAG — tìm context từ data rồi gửi cho LLM.

    Flow: cache check → queue → search → prompt → LLM → cache store
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

        # Check cache trước (pipeline.ask tự check)
        # Nếu cache miss → vào queue chờ LLM
        loop = asyncio.get_event_loop()
        async with llm_queue.acquire():
            answer = await loop.run_in_executor(
                None, pipeline.ask, request.question, False
            )

        return AskResponse(
            question=request.question,
            answer=answer,
            context=context_items,
        )

    except TimeoutError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
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
        "model": model,
        "prompt": request.question,
        "stream": False,
    }

    req = urllib.request.Request(
        server_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    try:
        loop = asyncio.get_event_loop()
        async with llm_queue.acquire():
            response = await loop.run_in_executor(
                None, urllib.request.urlopen, req
            )
            result = json.loads(response.read().decode("utf-8"))
        answer = result.get("response", "(Không có câu trả lời)")
    except TimeoutError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM server error: {exc}")

    return AskResponse(question=request.question, answer=answer)


# ═══════════════════════════════════════════════════════════
# STATIC FILES (Frontend) — phải đặt SAU tất cả API routes
# ═══════════════════════════════════════════════════════════

app.mount("/", StaticFiles(directory="fe", html=True), name="frontend")


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