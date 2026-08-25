# ⚡ x2t (X-to-Telegram Media Engine & Bot)

> High-performance, zero-third-party Twitter / X media extractor, downloader engine, and Telegram Bot.

`x2t` is a lightweight, robust Python engine and Telegram Bot designed to extract and download all media assets (videos, GIFs, and photos) from any X (Twitter) post URL with maximum available resolution and bitrate.

---

## 🚀 Features

- **Telegram Bot with Media Groups:** Automatically bundles multi-media posts (up to 4 videos/photos) into clean native Telegram albums (`send_media_group`).
- **Looping GIFs:** Converts Twitter GIFs into standard looping animations (`send_animation`).
- **Highest Quality:** Automatically selects the highest bitrate / 1080p / 4K MP4 stream for videos and original resolution (`name=orig`) for images.
- **Auto Server Cleanup:** All temporary media files downloaded to disk are automatically deleted right after being delivered to Telegram to conserve server disk space.
- **Anti-Flood & Rate Limiting:** Built-in middleware to protect the bot against spam and flood attacks.
- **SQLite Activity Tracker:** Tracks total downloads, active users, and includes admin commands (`/stats`, `/broadcast`).
- **Zero Third-Party Dependency:** Directly communicates with Twitter's native streaming and CDN infrastructure without relying on paid or third-party web scraper APIs.
- **Docker & Compose Ready:** 1-command deployment with Docker and Docker Compose.

---

## 📦 Installation & Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/x2t.git
cd x2t

pip install -e .
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Telegram Bot Token:

```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuvWXyz
ADMIN_IDS=[123456789]
DB_PATH=bot_database.sqlite3
TEMP_DOWNLOAD_DIR=./downloads/temp_bot
RATE_LIMIT_SECONDS=2.0
```

---

## 🤖 Running the Telegram Bot

### Option A: Direct Python Execution
```bash
python -m x2t.bot.main
```

### Option B: Docker Compose (Recommended for Production)
```bash
docker compose up -d --build
```

View logs:
```bash
docker compose logs -f
```

---

## 💻 CLI Usage

You can extract or download any post directly from your terminal:

```bash
# 1. Extract metadata and direct links (without downloading)
python -m x2t "https://x.com/username/status/1234567890"

# 2. Extract and download all media files to disk
python -m x2t "https://x.com/username/status/1234567890" --download --output ./my_downloads

# 3. Output structured JSON
python -m x2t "https://x.com/username/status/1234567890" --json
```

---

## 🐍 Python Library Usage

```python
import asyncio
import x2t

# 1. Synchronous
result = x2t.extract_media("https://x.com/username/status/1234567890")
print(f"Author: {result.author_name}, Media count: {result.media_count}")

# 2. Asynchronous Download
async def main():
    downloaded = await x2t.download_media_async("https://x.com/username/status/1234567890", output_dir="./downloads")
    for item in downloaded.items:
        print(item.type, item.resolution, item.local_path)

asyncio.run(main())
```

---

## 🧪 Testing

Run the full automated test suite with `pytest`:

```bash
pytest -v
```

---

## 📂 Project Structure

```
x2t/
├── x2t/
│   ├── __init__.py             # Public API: extract_media, download_media
│   ├── __main__.py             # CLI application entry point
│   ├── config.py               # Global settings & timeouts
│   ├── models.py               # Pydantic data models (MediaItem, PostMediaResult)
│   ├── core/
│   │   ├── extractor.py        # Central extraction coordinator
│   │   ├── ytdlp_backend.py    # yt-dlp native extraction backend
│   │   ├── syndication_backend.py # Direct syndication API fallback
│   │   └── downloader.py       # Async & Sync parallel file downloader
│   ├── utils/
│   │   ├── url_helper.py       # URL validation, tweet ID regex parser
│   │   └── media_helper.py     # Image/video format handlers & filenames
│   └── bot/
│       ├── __init__.py
│       ├── main.py             # Telegram Bot runner (aiogram 3)
│       ├── config.py           # Bot settings from .env
│       ├── database/
│       │   └── db.py           # Async SQLite user & download logger
│       ├── middlewares/
│       │   ├── throttling.py   # Anti-flood rate limiting
│       │   └── user_tracker.py # User registration middleware
│       ├── handlers/
│       │   ├── start.py        # /start, /help, /about commands
│       │   ├── downloader.py   # Twitter/X link interceptor & delivery
│       │   └── admin.py        # /stats, /broadcast commands
│       ├── keyboards/
│       │   └── inline.py       # Inline buttons (Tweet link, menu)
│       └── services/
│           └── media_sender.py # Smart media grouping & disk cleanup
├── Dockerfile                  # Production container
├── docker-compose.yml          # Compose service definition
├── .env.example                # Configuration template
├── tests/                      # 20 Automated unit & integration tests
├── pyproject.toml
└── requirements.txt
```
