"""Service for sending media to Telegram and cleaning up temporary files."""

import html
import logging
from pathlib import Path
from typing import List, Union
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo, Message

from x2t.bot.keyboards.inline import get_tweet_keyboard
from x2t.bot.services.mtproto_client import mtproto_client
from x2t.models import MediaType, PostMediaResult

logger = logging.getLogger("x2t.bot")


def format_tweet_caption(result: PostMediaResult, max_len: int = 800) -> str:
    """Format clean HTML caption for Telegram media."""
    author_str = ""
    if result.author_name:
        author_str = f"👤 <b>{html.escape(result.author_name)}</b>"
        if result.author_username:
            author_str += f" (<code>@{html.escape(result.author_username)}</code>)"
        author_str += "\n\n"

    text_str = ""
    if result.text:
        clean_text = html.escape(result.text.strip())
        if len(clean_text) > max_len:
            clean_text = clean_text[:max_len] + "..."
        text_str = f"{clean_text}\n\n"

    footer_str = "📥 <i>دانلود شده توسط @x2t_bot</i>"
    return f"{author_str}{text_str}{footer_str}"


def cleanup_temp_media(result: PostMediaResult):
    """Delete all downloaded temporary media files from disk."""
    for item in result.items:
        if item.local_path:
            try:
                p = Path(item.local_path)
                if p.exists():
                    p.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {item.local_path}: {e}")


async def send_post_media(
    bot: Bot,
    chat_id: Union[int, str],
    result: PostMediaResult,
    reply_to_message_id: int = None,
) -> List[Any := Message]:
    """Send extracted Twitter media to Telegram (via MTProto 2GB or Bot API) with auto-cleanup."""
    if not result.items:
        return []

    caption = format_tweet_caption(result)
    reply_markup = get_tweet_keyboard(result.canonical_url)
    sent_messages = []

    try:
        # Priority 1: Use MTProto Client (Supports up to 2000 MB / 2 GB with high-speed parallel uploads)
        if mtproto_client.is_ready():
            try:
                logger.info(f"Sending media via MTProto for chat {chat_id} (2GB mode)...")
                msgs = await mtproto_client.send_post_media_mtproto(
                    chat_id=chat_id,
                    result=result,
                    caption=caption,
                    reply_to_message_id=reply_to_message_id,
                )
                return msgs
            except Exception as e:
                logger.warning(f"MTProto sending failed: {e}. Falling back to standard Bot API...")

        # Priority 2: Standard Bot API
        if len(result.items) == 1:
            item = result.items[0]
            file = FSInputFile(item.local_path)

            try:
                if item.type == MediaType.GIF or item.is_gif:
                    msg = await bot.send_animation(
                        chat_id=chat_id,
                        animation=file,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        reply_to_message_id=reply_to_message_id,
                    )
                    sent_messages.append(msg)
                elif item.type == MediaType.VIDEO:
                    msg = await bot.send_video(
                        chat_id=chat_id,
                        video=file,
                        width=item.width,
                        height=item.height,
                        duration=int(item.duration_seconds) if item.duration_seconds else None,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        supports_streaming=True,
                        reply_to_message_id=reply_to_message_id,
                    )
                    sent_messages.append(msg)
                else:  # Photo
                    msg = await bot.send_photo(
                        chat_id=chat_id,
                        photo=file,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        reply_to_message_id=reply_to_message_id,
                    )
                    sent_messages.append(msg)
            except TelegramBadRequest as e:
                if "Request Entity Too Large" in str(e) or "file is too big" in str(e).lower():
                    logger.warning(f"File too big for local upload ({item.size_bytes} bytes). Sending streaming link...")
                    fallback_text = (
                        f"{caption}\n\n"
                        "⚠️ <b>حجم این ویدیو بیش از ۵۰ مگابایت است.</b>\n"
                        f"📥 <a href=\"{item.url}\">برای دانلود مستقیم با بالاترین کیفیت اینجا کلیک کنید</a>"
                    )
                    msg = await bot.send_message(
                        chat_id=chat_id,
                        text=fallback_text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        reply_to_message_id=reply_to_message_id,
                    )
                    sent_messages.append(msg)
                else:
                    raise

        else:  # Multi-Media
            media_group = []
            for idx, item in enumerate(result.items):
                file = FSInputFile(item.local_path)
                item_caption = caption if idx == 0 else None
                item_parse_mode = "HTML" if idx == 0 else None

                if item.type == MediaType.PHOTO:
                    media_group.append(
                        InputMediaPhoto(
                            media=file,
                            caption=item_caption,
                            parse_mode=item_parse_mode,
                        )
                    )
                else:
                    media_group.append(
                        InputMediaVideo(
                            media=file,
                            width=item.width,
                            height=item.height,
                            duration=int(item.duration_seconds) if item.duration_seconds else None,
                            caption=item_caption,
                            parse_mode=item_parse_mode,
                            supports_streaming=True,
                        )
                    )

            group_msgs = await bot.send_media_group(
                chat_id=chat_id,
                media=media_group,
                reply_to_message_id=reply_to_message_id,
            )
            sent_messages.extend(group_msgs)

            btn_msg = await bot.send_message(
                chat_id=chat_id,
                text="🔗 <i>اطلاعات و لینک پست در توییتر:</i>",
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            sent_messages.append(btn_msg)

        return sent_messages

    finally:
        cleanup_temp_media(result)
