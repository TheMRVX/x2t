# x2t

دانلود مدیا از توییتر (X) و ارسال به تلگرام — با پشتیبانی از آپلود تا ۲ گیگابایت.

[English](#english) • [فارسی](#فارسی)

---

## English

### What is x2t?

x2t is a Python tool that downloads videos, photos, and GIFs from Twitter/X posts and sends them to Telegram. It works as a Telegram bot, a CLI tool, or a Python library.

The key difference from similar tools: x2t uses Telegram's MTProto protocol (via Pyrogram) for uploads, which means it can send files up to **2 GB** — bypassing Telegram Bot API's 50 MB limit.

### Features

**Media Extraction**
- Downloads videos (up to 4K), photos (original resolution), and GIFs from any tweet
- Multi-backend extraction: tries FxTwitter, yt-dlp, Twitter GraphQL, and Syndication CDN as fallbacks
- Handles NSFW/age-restricted content with Twitter auth cookie support

**Profile Downloader**
- Downloads media from an entire user's timeline
- Cursor-based pagination for fetching all posts
- Filters: exclude retweets, quote tweets, third-party media (`From @other`), select media types
- Configurable limits: unlimited, or 10/25/50/100 posts

**Telegram Bot**
- Interactive inline menus with checkbox toggles for profile filters
- Live progress message pinned to chat with post/file counters and stop button
- Multi-photo/video tweets sent as native Telegram albums
- Private/public access mode with user allowlisting
- Admin dashboard: `/stats`, `/broadcast`, `/history`

**Technical**
- Async architecture with `aiogram` + `Pyrogram`
- SQLite (WAL mode) for download history and user tracking
- In-memory TTL cache (5 min) to avoid duplicate API requests
- Auto-cleanup of temp files after delivery

### Quick Start

**Requirements:** Python 3.10+, FFmpeg

```bash
git clone https://github.com/TheMRVX/x2t.git
cd x2t
pip install -e .
```

Copy and edit the config:

```bash
cp .env.example .env
```

```env
BOT_TOKEN=your_bot_token
API_ID=your_api_id          # from my.telegram.org
API_HASH=your_api_hash      # from my.telegram.org

IS_PRIVATE=true              # true = only allowed users, false = public
ADMIN_IDS=[123456789]
ALLOWED_USER_IDS=[]

# Optional
TWITTER_AUTH_TOKEN=           # for NSFW content
CLEAN_CAPTION=true            # minimal captions without author info
```

### Usage

**Telegram Bot:**
```bash
python -m x2t.bot.main
```

**Docker:**
```bash
docker compose up -d --build
docker compose logs -f    # view logs
```

**CLI:**
```bash
# Extract media info (no download)
x2t "https://x.com/user/status/123"

# Download media files
x2t "https://x.com/user/status/123" --download --output ./media

# JSON output
x2t "https://x.com/user/status/123" --json
```

**Python SDK:**
```python
import x2t

# Extract metadata
result = x2t.extract_media("https://x.com/user/status/123")
for item in result.items:
    print(f"{item.type}: {item.resolution} → {item.url}")

# Download files
result = x2t.download_media("https://x.com/user/status/123", output_dir="./downloads")

# Async download
result = await x2t.download_media_async("https://x.com/user/status/123")
```

**Profile streaming:**
```python
import asyncio
from x2t.core.profile_extractor import profile_extractor
from x2t.models import ProfileFilterOptions

async def main():
    options = ProfileFilterOptions(
        include_videos=True,
        include_photos=True,
        include_retweets=False,
        include_sourced_media=False,
        limit=50,
    )
    async for post in profile_extractor.iter_profile_media_tweets_stream("NASA", options):
        print(f"Tweet {post.tweet_id}: {len(post.media_items)} media items")

asyncio.run(main())
```

### Bot Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | All | Welcome and instructions |
| `/help` | All | Usage guide |
| `/history` | All | Recent 5 downloads |
| `/about` | All | Version info |
| `/mode [private/public]` | Admin | Toggle access mode |
| `/caption [clean/full]` | Admin | Toggle caption style |
| `/stats` | Admin | User/download statistics |
| `/allow <id>` | Admin | Whitelist a user |
| `/disallow <id>` | Admin | Remove a user |
| `/set_cookie <token>` | Admin | Set Twitter auth for NSFW |
| `/broadcast <msg>` | Admin | Message all users |

### Architecture

```
x2t/
├── __init__.py          # Public API (extract_media, download_media, etc.)
├── __main__.py          # CLI entry point
├── config.py            # Settings (Pydantic)
├── models.py            # Data models (MediaItem, PostMediaResult, etc.)
├── exceptions.py        # Error hierarchy
├── logger.py            # Logging setup (Rich)
├── core/                # Extraction backends & downloader
├── bot/                 # Telegram bot (aiogram + Pyrogram)
└── utils/               # Helpers
```

Extraction pipeline:

```
Tweet URL → FxTwitter → yt-dlp → GraphQL → Syndication CDN → Download → Telegram MTProto
                ↓ (if fails)  ↓ (if fails)  ↓ (if fails)
              fallback      fallback       fallback
```

### License

AGPL-3.0 — see [LICENSE](LICENSE).

---

## فارسی

### x2t چیست؟

x2t یک ابزار پایتونی برای دانلود ویدیو، عکس و گیف از توییتر/X و ارسال مستقیم به تلگرام است. هم به عنوان ربات تلگرام، هم از خط فرمان (CLI) و هم به عنوان کتابخانه پایتون قابل استفاده‌ست.

تفاوت اصلی با ابزارهای مشابه: x2t از پروتکل MTProto تلگرام (از طریق Pyrogram) استفاده می‌کنه، یعنی فایل‌های تا **۲ گیگابایت** رو مستقیم آپلود می‌کنه — بدون محدودیت ۵۰ مگابایتی Bot API.

### امکانات

- دانلود ویدیو (تا 4K)، عکس (رزولوشن اصلی) و گیف از هر توییت
- استخراج چندلایه: FxTwitter → yt-dlp → GraphQL → Syndication CDN
- پشتیبانی از محتوای NSFW با کوکی توییتر
- دانلود کل تایم‌لاین پروفایل با فیلتر ریتوییت، کوت‌توییت، مدیای شخص ثالث
- منوی اینلاین با چک‌باکس برای تنظیم فیلترها
- پیام وضعیت پین‌شده با شمارنده زنده و دکمه توقف
- ارسال آلبومی پست‌های چندرسانه‌ای
- حالت عمومی/خصوصی با لیست مجاز کاربران
- پنل ادمین: آمار، پیام همگانی، تاریخچه

### نصب سریع

**پیش‌نیازها:** Python 3.10+, FFmpeg

```bash
git clone https://github.com/TheMRVX/x2t.git
cd x2t
pip install -e .
cp .env.example .env
# فایل .env رو ویرایش کنید
```

### اجرا

```bash
# ربات تلگرام
python -m x2t.bot.main

# داکر
docker compose up -d --build
```

### خط فرمان (CLI)

```bash
# فقط اطلاعات مدیا
x2t "https://x.com/user/status/123"

# دانلود فایل‌ها
x2t "https://x.com/user/status/123" --download --output ./media

# خروجی JSON
x2t "https://x.com/user/status/123" --json
```

### استفاده در پایتون

```python
import x2t

result = x2t.extract_media("https://x.com/user/status/123")
for item in result.items:
    print(f"{item.type}: {item.url}")

# دانلود
result = x2t.download_media("https://x.com/user/status/123", output_dir="./downloads")
```

### دستورات ربات

| دستور | دسترسی | توضیح |
|-------|--------|-------|
| `/start` | همه | خوش‌آمد و راهنما |
| `/help` | همه | راهنمای استفاده |
| `/history` | همه | ۵ دانلود اخیر |
| `/about` | همه | اطلاعات نسخه |
| `/mode` | ادمین | تغییر حالت دسترسی |
| `/caption` | ادمین | تغییر استایل کپشن |
| `/stats` | ادمین | آمار کاربران و دانلودها |
| `/allow <id>` | ادمین | اضافه کردن کاربر مجاز |
| `/disallow <id>` | ادمین | حذف کاربر مجاز |
| `/set_cookie <token>` | ادمین | تنظیم کوکی توییتر |
| `/broadcast <msg>` | ادمین | ارسال پیام به همه |

### لایسنس

AGPL-3.0 — فایل [LICENSE](LICENSE) رو ببینید.
