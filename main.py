#!/usr/bin/env python3
"""
League of Legends RAG-powered Q&A
==================================

Hệ thống hỏi đáp thông minh về League of Legends, sử dụng:
- Dữ liệu crawl từ Riot Data Dragon (champions, items, runes, spells...)
- RAG (Retrieval-Augmented Generation) để tìm context liên quan
- Ollama LLM (qua ngrok) để sinh câu trả lời

Usage:
    python main.py                          # Hỏi đáp với RAG + LLM
    python main.py --offline                # Chỉ tìm kiếm data, không gọi LLM
    python main.py --no-rag                 # Gửi thẳng câu hỏi cho LLM (không RAG)
    python main.py --show-context           # Hiển thị context được tìm thấy
    python main.py --question "Ahri build?" # Hỏi trực tiếp qua CLI
"""

import argparse
import json
import sys
import urllib.request

from rag.pipeline import RAGPipeline


# ═══════════════════════════════════════════════════════════
# CẤU HÌNH
# ═══════════════════════════════════════════════════════════

# Trỏ đích đến đúng cổng nhận thư của trạm trung chuyển
SERVER_URL = "http://127.0.0.1:8080/nhan-tin-nhan"

# Tên mô hình LLM (đảm bảo đã được tải sẵn trên server)
MODEL_NAME = "qwen3:14b"

# Đường dẫn tới dữ liệu đã crawl
DATA_DIR = "league-of-legend/data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lol-rag",
        description="🎮 League of Legends RAG Q&A — Hỏi đáp thông minh với dữ liệu game",
    )
    parser.add_argument(
        "--question", "-q", type=str, default=None,
        help="Câu hỏi (nếu không cung cấp, sẽ hỏi interactive)",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Chế độ offline: chỉ tìm kiếm data, không gọi LLM",
    )
    parser.add_argument(
        "--no-rag", action="store_true",
        help="Gửi thẳng câu hỏi cho LLM mà không có context từ RAG",
    )
    parser.add_argument(
        "--show-context", action="store_true",
        help="Hiển thị dữ liệu context được tìm thấy trước khi gửi cho LLM",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Dùng prompt ngắn gọn hơn (cho model có context window nhỏ)",
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="Số lượng kết quả tìm kiếm sử dụng cho context (default: 5)",
    )
    parser.add_argument(
        "--server-url", type=str, default=SERVER_URL,
        help="URL của Ollama server (ngrok)",
    )
    parser.add_argument(
        "--model", type=str, default=MODEL_NAME,
        help="Tên mô hình LLM",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Chế độ interactive: hỏi liên tục",
    )
    return parser.parse_args()


def query_llm_direct(question: str, server_url: str, model_name: str) -> str:
    """Gửi câu hỏi trực tiếp đến LLM mà không có RAG context."""
    payload = {
        "ten_mo_hinh": model_name,
        "cau_hoi": question,
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

    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode("utf-8"))
    return result.get("cau_tra_loi_tu_he_thong", "(Không có câu trả lời)")


def run_single_query(pipeline: RAGPipeline, question: str, args: argparse.Namespace) -> None:
    """Xử lý một câu hỏi."""
    print(f"\n🎯 Câu hỏi: {question}")
    print("─" * 60)

    try:
        if args.no_rag:
            # Chế độ không RAG — gửi thẳng cho LLM
            print("⚡ Chế độ NO-RAG: gửi thẳng cho LLM...")
            answer = query_llm_direct(question, args.server_url, args.model)
        elif args.offline:
            # Chế độ offline — chỉ tìm kiếm data
            answer = pipeline.ask_offline(question)
        else:
            # Chế độ RAG đầy đủ
            answer = pipeline.ask(question, show_context=args.show_context)

        print("\n--- HỆ THỐNG TRẢ LỜI ---")
        print(answer)
        print("─" * 60)

    except ConnectionError as exc:
        print(f"\n⚠ Lỗi kết nối đến LLM server: {exc}")
        print("💡 Thử chế độ offline: python main.py --offline")
    except Exception as exc:
        print(f"\n❌ Lỗi: {exc}")


def main() -> None:
    args = parse_args()

    # Khởi tạo RAG pipeline (trừ chế độ no-rag)
    pipeline = None
    if not args.no_rag:
        pipeline = RAGPipeline(
            data_dir=DATA_DIR,
            server_url=args.server_url,
            model_name=args.model,
            top_k=args.top_k,
            compact_mode=args.compact,
        )
        pipeline.initialize()

    # Xác định câu hỏi
    if args.question:
        run_single_query(pipeline, args.question, args)

    elif args.interactive:
        # Chế độ interactive
        print("\n🎮 League of Legends RAG Q&A — Interactive Mode")
        print("Gõ 'quit' hoặc 'exit' để thoát.\n")

        while True:
            try:
                question = input("❓ Câu hỏi: ").strip()
                if question.lower() in ("quit", "exit", "q"):
                    print("👋 Tạm biệt!")
                    break
                if not question:
                    continue
                run_single_query(pipeline, question, args)
                print()
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Tạm biệt!")
                break
    else:
        # Câu hỏi mặc định
        default_question = "Tại sao hiện tại người ta lại lên đai lưng hextech cho ahri trong liên minh huyền thoại?"
        run_single_query(pipeline, default_question, args)


if __name__ == "__main__":
    main()