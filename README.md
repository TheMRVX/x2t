# ⚡ x2t (X-to-Telegram Media Engine)

> High-performance, zero-third-party Twitter / X media extractor and downloader engine.

`x2t` is a lightweight, robust Python engine designed to extract and download all media assets (videos, GIFs, and photos) from any X (Twitter) post URL with maximum available resolution and bitrate.

---

## 🚀 Features

- **Multi-Media Support:** Seamlessly extracts and downloads up to 4 media items per post (multi-video, photo galleries, or mixed media).
- **Highest Quality:** Automatically selects the highest bitrate / 1080p / 4K MP4 stream for videos and original resolution (`name=orig`) for images.
- **GIF Optimization:** Handles Twitter GIFs natively as standard, lightweight MP4 video animations, perfectly suited for Telegram (`send_animation` / `send_video`).
- **Zero Third-Party Dependency:** Directly communicates with Twitter's native streaming and CDN infrastructure without relying on paid or third-party web scraper APIs.
- **HLS & Progressive MP4:** Built-in FFmpeg integration for seamless stream assembly when needed.
- **Modern Async & Sync:** Offers both synchronous and asynchronous methods (`asyncio` / `httpx`) with parallel concurrent chunk downloading.
- **Strong Typing:** Fully validated with Pydantic models for easy integration into bots, REST APIs, or background workers.

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/x2t.git
cd x2t

# Install dependencies
pip install -e .
```

### System Requirements
- Python 3.10+
- `ffmpeg` (for HLS stream processing): `apt-get install ffmpeg`

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

### Synchronous Usage
```python
import x2t

# 1. Extract info only
result = x2t.extract_media("https://x.com/username/status/1234567890")
print(f"Author: {result.author_name} (@{result.author_username})")
print(f"Total media: {result.media_count}")

for item in result.items:
    print(f"[{item.type.value}] {item.resolution} -> {item.url}")

# 2. Download all media files to disk
downloaded = x2t.download_media("https://x.com/username/status/1234567890", output_dir="./downloads")
for item in downloaded.items:
    print(f"Saved {item.filename} ({item.size_bytes} bytes) to {item.local_path}")
```

### Asynchronous Usage (Ideal for Telegram Bots)
```python
import asyncio
import x2t

async def handle_telegram_message(tweet_url: str):
    # Asynchronously extract and download in parallel
    result = await x2t.download_media_async(tweet_url, output_dir="./temp_bot_media")
    
    for item in result.items:
        if item.type == x2t.MediaType.GIF:
            # Send as Telegram Animation (GIF)
            # await bot.send_animation(chat_id, animation=open(item.local_path, "rb"))
            pass
        elif item.type == x2t.MediaType.VIDEO:
            # Send as Telegram Video
            # await bot.send_video(chat_id, video=open(item.local_path, "rb"), width=item.width, height=item.height)
            pass
        elif item.type == x2t.MediaType.PHOTO:
            # Send as Telegram Photo
            # await bot.send_photo(chat_id, photo=open(item.local_path, "rb"))
            pass

asyncio.run(handle_telegram_message("https://x.com/username/status/1234567890"))
```

---

## 🧪 Testing

Run the automated test suite with `pytest`:

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
│   └── utils/
│       ├── url_helper.py       # URL validation, tweet ID regex parser
│       └── media_helper.py     # Image/video format handlers & filenames
├── tests/
│   ├── test_extractor.py       # Integration tests
│   ├── test_media_helper.py    # Unit tests for media helpers
│   ├── test_models.py          # Unit tests for data models
│   └── test_url_helper.py      # Unit tests for URL parser
├── pyproject.toml
├── requirements.txt
└── README.md
```
