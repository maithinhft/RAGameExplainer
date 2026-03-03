# 🎮 League of Legends Data Crawler

Production-quality Python crawler cho dữ liệu game **League of Legends** sử dụng [Riot Data Dragon API](https://developer.riotgames.com/docs/lol#data-dragon) — **không cần API key**.

## ✨ Tính năng

- **Crawl toàn bộ dữ liệu game**: Champions, Items, Runes, Summoner Spells, Maps, Patch Versions
- **Chi tiết từng tướng**: Stats, spells (Q/W/E/R), passive, skins, tips
- **Async & nhanh**: Sử dụng `aiohttp` với concurrent requests, retry tự động
- **Caching thông minh**: Cache HTTP responses ra disk, tránh re-fetch
- **Đa ngôn ngữ**: Hỗ trợ tiếng Việt (`vi_VN`), tiếng Anh (`en_US`), và 10+ ngôn ngữ khác
- **Nhiều output format**: JSON files hoặc SQLite database (hoặc cả hai)
- **Download ảnh**: Champion portraits, item icons, spell icons
- **CLI đầy đủ**: Chọn category, version, ngôn ngữ, format qua command line

## 📦 Cài đặt

```bash
cd league-of-legend
pip install -r requirements.txt
```

**Yêu cầu**: Python ≥ 3.10

## 🚀 Sử dụng

### Crawl tất cả dữ liệu

```bash
python main.py --all
```

### Crawl theo category

```bash
python main.py --champions              # Chỉ tướng
python main.py --items                  # Chỉ trang bị
python main.py --runes                  # Chỉ bảng ngọc
python main.py --spells                 # Chỉ phép bổ trợ
python main.py --maps                   # Chỉ bản đồ
python main.py --patches                # Chỉ các bản cập nhật
python main.py --champions --items      # Kết hợp nhiều category
```

### Tùy chọn ngôn ngữ

```bash
python main.py --all --lang vi_VN       # Tiếng Việt
python main.py --all --lang ko_KR       # Tiếng Hàn
python main.py --all --lang ja_JP       # Tiếng Nhật
```

### Chọn bản cập nhật cụ thể

```bash
python main.py --all --version 15.24.1  # Patch 15.24
python main.py --all --version 14.1.1   # Patch 14.1
```

### Output format

```bash
python main.py --all --output json      # JSON files (mặc định)
python main.py --all --output sqlite    # SQLite database
python main.py --all --output both      # Cả hai
```

### Download ảnh

```bash
python main.py --all --download-images  # Download champion/item/spell images
```

### Tùy chọn nâng cao

```bash
python main.py --all --output-dir my_data   # Thư mục output khác
python main.py --all --concurrency 20       # Tăng concurrent requests
python main.py --all --no-cache             # Tắt cache
python main.py --all --verbose              # Debug logging
```

## 📂 Cấu trúc output

### JSON Output

```
data/
├── champions.json          # Danh sách tất cả tướng (chi tiết)
├── champions/              # File riêng từng tướng
│   ├── Aatrox.json
│   ├── Ahri.json
│   └── ...
├── items.json              # Tất cả trang bị
├── runes.json              # Tất cả bảng ngọc
├── spells.json             # Tất cả phép bổ trợ
├── maps.json               # Bản đồ
├── patches.json            # Lịch sử patch
└── images/                 # Ảnh (nếu --download-images)
    ├── champions/
    ├── items/
    └── spells/
```

### SQLite Output

```
data/
└── lol_data.db             # Database với các bảng:
    ├── champions           #   - champion_id, name, stats, spells, skins...
    ├── items               #   - item_id, name, gold, stats, build path...
    ├── rune_paths          #   - path_id, name, runes...
    ├── runes               #   - rune_id, name, description...
    ├── summoner_spells     #   - spell_id, name, cooldown, modes...
    ├── maps                #   - map_id, name...
    ├── patches             #   - version, major, minor, patch
    └── crawl_metadata      #   - crawl timestamp, version, language
```

## 🏗️ Kiến trúc

```
league-of-legend/
├── main.py                 # CLI entry point (argparse)
├── config/
│   └── settings.py         # URLs, constants, runtime settings
├── src/
│   ├── http_client.py      # Async HTTP + retry + cache
│   ├── crawlers/           # Crawler modules
│   │   ├── base.py         # Abstract base crawler
│   │   ├── version.py      # Patch version crawler
│   │   ├── champion.py     # Champion crawler (list + detail)
│   │   ├── item.py         # Item crawler
│   │   ├── rune.py         # Rune crawler
│   │   ├── spell.py        # Summoner spell crawler
│   │   └── map.py          # Map crawler
│   ├── models/             # Typed dataclass models
│   │   ├── champion.py     # Champion, Stats, Spell, Skin
│   │   ├── item.py         # Item, ItemGold
│   │   ├── rune.py         # Rune, RunePath
│   │   ├── spell.py        # SummonerSpell
│   │   └── patch.py        # PatchVersion
│   ├── storage/            # Storage backends
│   │   ├── base.py         # Storage interface
│   │   ├── json_storage.py # JSON file output
│   │   └── sqlite_storage.py # SQLite database output
│   └── utils/              # Logger setup
├── requirements.txt
└── pyproject.toml
```

## 📊 Dữ liệu mẫu

### Champion (ví dụ Ahri)

```json
{
  "champion_id": "Ahri",
  "key": 103,
  "name": "Ahri",
  "title": "the Nine-Tailed Fox",
  "tags": ["Mage", "Assassin"],
  "stats": {
    "hp": 590,
    "attack_damage": 53,
    "move_speed": 330,
    "...": "..."
  },
  "spells": [
    {"name": "Orb of Deception", "cooldown": [7, 7, 7, 7, 7], "...": "..."},
    "..."
  ],
  "skins": [
    {"name": "default", "num": 0},
    {"name": "Dynasty Ahri", "num": 1},
    "..."
  ]
}
```

## 📝 License

MIT
