# 🎮 RAGameExplainer

Hệ thống hỏi đáp thông minh về **League of Legends** sử dụng **RAG** (Retrieval-Augmented Generation) — kết hợp dữ liệu game crawl từ Riot Data Dragon với LLM local (Ollama) để trả lời chính xác các câu hỏi về tướng, trang bị, bảng ngọc, meta,...

## ✨ Tính năng chính

- **🔍 RAG Search**: Tìm kiếm thông minh kết hợp TF-IDF + keyword + fuzzy matching
- **🤖 LLM Integration**: Kết nối Ollama local server để sinh câu trả lời
- **📡 REST API**: FastAPI server với Swagger docs tự động
- **🔄 Auto-refresh**: Tự động crawl lại dữ liệu mới mỗi 1 tiếng
- **🌐 Đa ngôn ngữ**: Hỗ trợ tiếng Việt ↔ tiếng Anh (alias mapping)
- **📊 891+ documents**: Champions, Items, Runes, Spells, Maps, Patches

## 🏗️ Kiến trúc

```
User Question
    │
    ▼
┌─────────────────────────────────────────┐
│           FastAPI Server (:8000)         │
│                                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │ /search  │  │  /ask    │  │/refresh│ │
│  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │             │            │      │
│       ▼             ▼            ▼      │
│  ┌──────────────────────────────────┐   │
│  │         RAG Pipeline             │   │
│  │  Search → Context → Prompt → LLM│   │
│  └──────────────────────────────────┘   │
│       │                      │          │
│       ▼                      ▼          │
│  ┌──────────┐        ┌────────────┐     │
│  │ Indexer   │        │  Ollama    │     │
│  │ (891 docs)│        │  (local)   │     │
│  └──────────┘        └────────────┘     │
│       ▲                                 │
│       │                                 │
│  ┌──────────┐                           │
│  │ Crawler   │ ← Riot Data Dragon API   │
│  │ (hourly)  │                          │
│  └──────────┘                           │
└─────────────────────────────────────────┘
```

## 📦 Cài đặt

```bash
# Clone repo
git clone https://github.com/maithinhft/RAGameExplainer.git
cd RAGameExplainer

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

**Yêu cầu:** Python ≥ 3.10, [Ollama](https://ollama.ai) (cho LLM)

## 🚀 Chạy server

```bash
source venv/bin/activate
python main.py
```

Server chạy tại `http://localhost:8000` — Swagger docs tại `http://localhost:8000/docs`

> Khi khởi động, server sẽ tự động crawl dữ liệu mới từ Riot Data Dragon, sau đó tự động cập nhật mỗi 1 tiếng.

## 📡 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/health` | Health check + trạng thái pipeline |
| `GET` | `/stats` | Thống kê data (số documents, categories, thời gian refresh) |
| `POST` | `/search` | Tìm kiếm dữ liệu game (không gọi LLM) |
| `POST` | `/ask` | **RAG đầy đủ**: search context → augmented prompt → LLM |
| `POST` | `/ask-direct` | Gửi thẳng cho LLM (không RAG) |
| `POST` | `/refresh` | Cập nhật dữ liệu thủ công (xóa cũ → crawl mới) |

### Ví dụ gọi API

**Tìm kiếm data:**
```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "ahri hextech", "top_k": 3}'
```

**Hỏi đáp RAG** (cần Ollama chạy):
```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Tại sao lên đai lưng hextech cho Ahri?",
    "show_context": true,
    "top_k": 5
  }'
```

**Hỏi trực tiếp LLM** (không RAG):
```bash
curl -X POST http://localhost:8000/ask-direct \
  -H 'Content-Type: application/json' \
  -d '{"question": "Ahri counter ai?"}'
```

**Cập nhật dữ liệu thủ công:**
```bash
curl -X POST http://localhost:8000/refresh
```

## ⚙️ Cấu hình

Cấu hình qua **environment variables**:

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `LLM_SERVER_URL` | `http://127.0.0.1:11434/api/generate` | URL Ollama API |
| `LLM_MODEL` | `qwen3:14b` | Tên model LLM |
| `DATA_DIR` | `league-of-legend/data` | Thư mục chứa data crawl |
| `CRAWLER_DIR` | `league-of-legend` | Thư mục gốc crawler |
| `REFRESH_INTERVAL_SECONDS` | `3600` | Chu kỳ auto-refresh (giây) |
| `PORT` | `8000` | Port server |

```bash
# Ví dụ: đổi model và port
LLM_MODEL=llama3:8b PORT=3000 python main.py
```

## 📂 Cấu trúc project

```
RAGameExplainer/
├── main.py                     # FastAPI server + scheduler
├── requirements.txt            # Dependencies
├── rag/                        # RAG module
│   ├── indexer.py              # Load JSON → searchable documents
│   ├── search.py               # TF-IDF + keyword + fuzzy search
│   ├── prompt_builder.py       # Context-augmented prompts
│   └── pipeline.py             # End-to-end orchestration
├── league-of-legend/           # Data crawler
│   ├── main.py                 # Crawler CLI
│   ├── config/settings.py      # DDragon URLs & config
│   ├── src/
│   │   ├── http_client.py      # Async HTTP + retry + cache
│   │   ├── crawlers/           # Champion, Item, Rune, Spell, Map, Version
│   │   ├── models/             # Typed dataclasses
│   │   └── storage/            # JSON + SQLite output
│   └── data/                   # Crawled data (auto-generated)
│       ├── champions.json
│       ├── items.json
│       ├── runes.json
│       ├── spells.json
│       ├── maps.json
│       └── patches.json
└── venv/                       # Virtual environment
```

## 📊 Dữ liệu

Dữ liệu được crawl từ [Riot Data Dragon API](https://developer.riotgames.com/docs/lol#data-dragon) (không cần API key):

| Category | Số lượng | Chi tiết |
|----------|----------|----------|
| Champions | 172 | Stats, spells (Q/W/E/R), passive, skins, tips |
| Items | 688 | Gold, stats, build paths, tags |
| Rune Paths | 5 | Domination, Inspiration, Precision, Resolve, Sorcery |
| Summoner Spells | 18 | Cooldown, modes, level requirement |
| Maps | 7 | Map metadata |
| Patches | 485+ | Version history (v3.7 → latest) |

## 🔍 RAG Search Engine

Hệ thống search kết hợp 3 phương pháp:

1. **TF-IDF** — cosine similarity trên toàn bộ corpus
2. **Keyword matching** — exact match tên tướng, trang bị
3. **Fuzzy matching** — xử lý typo và partial matches

Đặc biệt hỗ trợ **Vietnamese → English alias mapping**:
- "đai lưng hextech" → Hextech Rocketbelt
- "mũ phù thủy" → Rabadon's Deathcap
- "xạ thủ" → Marksman/ADC
- "tốc biến" → Flash

## 📝 License

MIT
