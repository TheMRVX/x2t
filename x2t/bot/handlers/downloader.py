"""X / Twitter link downloader message handler with structured error management."""

import re
import uuid
from aiogram import F, Router
from aiogram.types import Message

import x2t
from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.bot.services.media_sender import send_post_media
from x2t.exceptions import NoMediaFoundError, X2TError
from x2t.logger import get_logger
from x2t.utils.url_helper import extract_tweet_id

logger = get_logger("x2t.bot.downloader")
router = Router(name="downloader_router")

# Regex to detect X / Twitter URLs anywhere in user text
X_URL_REGEX = re.compile(
    r"https?://(?:www\.|mobile\.|m\.)?(?:twitter\.com|x\.com)/(?:#!/)?(?:[A-Za-z0-9_]+)/status/\d+",
    re.IGNORECASE,
)


@router.message(F.text.regexp(X_URL_REGEX))
async def handle_x_link(message: Message, db: Database):
    """Detect Twitter / X links in message and download media."""
    text = message.text.strip()
    match = X_URL_REGEX.search(text)
    if not match:
        return

    url = match.group(0)
    tweet_id = extract_tweet_id(url)
    user_id = message.from_user.id if message.from_user else 0

    # 1. Send initial progress message
    status_msg = await message.reply("⏳ <b>در حال بررسی و دریافت اطلاعات پست...</b>", parse_mode="HTML")

    try:
        # 2. Update status to downloading
        await status_msg.edit_text("📥 <b>در حال دانلود با بالاترین کیفیت...</b>", parse_mode="HTML")

        # 3. Download media asynchronously
        temp_dir = bot_config.temp_download_dir / f"user_{user_id}_{tweet_id}"
        result = await x2t.download_media_async(url, output_dir=temp_dir)

        if not result.has_media:
            raise NoMediaFoundError(f"Tweet {tweet_id} has no media.")

        # 4. Update status to uploading
        await status_msg.edit_text("🚀 <b>در حال ارسال فایل‌ها به تلگرام...</b>", parse_mode="HTML")

        # 5. Deliver media to chat
        await send_post_media(
            bot=message.bot,
            chat_id=message.chat.id,
            result=result,
            reply_to_message_id=message.message_id,
        )

        # 6. Record download stats in DB
        await db.record_download(
            user_id=user_id,
            tweet_id=result.tweet_id,
            media_count=result.media_count,
        )

        # 7. Delete temporary status message
        try:
            await status_msg.delete()
        except Exception:
            pass

    except X2TError as e:
        logger.warning(f"Domain error [{e.error_code}] downloading {url} for user {user_id}: {e.message}")
        await status_msg.edit_text(e.format_telegram_error(), parse_mode="HTML")

    except Exception as e:
        incident_id = str(uuid.uuid4())[:8].upper()
        logger.error(
            f"Unhandled exception [Incident #{incident_id}] processing {url} for user {user_id}: {e}",
            exc_info=True,
        )
        error_text = (
            "❌ <b>خطا در پردازش و دانلود مدیا!</b>\n\n"
            "متأسفانه در دریافت محتوای این پست خطایی رخ داد.\n\n"
            f"🔖 <code>کد پیگیری خطا: #{incident_id}</code>\n"
            "💡 <i>لطفاً از صحت لینک اطمینان حاصل کرده و مجدداً تلاش نمایید.</i>"
        )
        await status_msg.edit_text(error_text, parse_mode="HTML")
