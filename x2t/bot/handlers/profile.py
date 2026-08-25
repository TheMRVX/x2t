"""Profile timeline and advanced batch media download handlers with streaming extraction and pinned progress."""

import asyncio
import html
import logging
import uuid
from typing import Dict
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import x2t
from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.bot.keyboards.profile_inline import get_cancel_batch_keyboard, get_profile_settings_keyboard
from x2t.bot.services.media_sender import send_post_media
from x2t.core.profile_extractor import profile_extractor
from x2t.models import ProfileFilterOptions, ProfileInfo
from x2t.utils.url_helper import extract_profile_username, extract_tweet_id

logger = logging.getLogger("x2t.bot.profile")
router = Router(name="profile_router")

# User filter options state: user_id:username -> ProfileFilterOptions
user_profile_states: Dict[str, ProfileFilterOptions] = {}

# Active batch download tasks: task_id -> asyncio.Task
active_tasks: Dict[str, asyncio.Task] = {}


def _get_state_key(user_id: int, username: str) -> str:
    return f"{user_id}:{username.lower()}"


def _format_profile_card(info: ProfileInfo) -> str:
    """Format clean HTML profile preview message."""
    followers_str = f"{info.followers_count:,}" if info.followers_count else "N/A"
    media_str = f"{info.media_count:,}" if info.media_count else "مشخص نیست"

    header = f"👤 <b>پروفایل توییتر: {html.escape(info.name)}</b> (<code>@{html.escape(info.username)}</code>)\n"
    if info.bio:
        header += f"📝 <i>{html.escape(info.bio.strip()[:150])}</i>\n\n"
    else:
        header += "\n"

    stats = (
        f"📊 <b>تعداد دنبال‌کنندگان:</b> {followers_str}\n"
        f"🖼️ <b>تعداد کل مدیاها:</b> ~{media_str}\n\n"
        "⚙️ <b>فیلترهای دریافت محتوا (روی دکمه‌ها کلیک کنید):</b>"
    )
    return header + stats


@router.message(F.text)
async def handle_profile_or_text(message: Message):
    """Detect profile URLs / @handles and display interactive filter panel."""
    text = message.text.strip()

    # Skip if it is a specific tweet status URL
    if extract_tweet_id(text):
        return

    username = extract_profile_username(text)
    if not username:
        return

    status_msg = await message.reply("🔍 <b>در حال بررسی و دریافت اطلاعات پروفایل...</b>", parse_mode="HTML")

    try:
        # Fetch profile metadata
        info = profile_extractor.get_profile_info(username)

        # Initialize default filter state (Strict Original Only mode, Limit 0 = Unlimited/All)
        state_key = _get_state_key(message.from_user.id, info.username)
        options = ProfileFilterOptions(
            include_videos=True,
            include_photos=True,
            include_gifs=True,
            include_retweets=False,        # Default: Exclude Retweets
            include_sourced_media=False,   # Default: Exclude 'From @other'
            include_quotes=False,          # Default: Exclude Quote tweets
            limit=0,                       # Default: 0 = Unlimited / All available
        )
        user_profile_states[state_key] = options

        card_text = _format_profile_card(info)
        markup = get_profile_settings_keyboard(info.username, options)

        await status_msg.edit_text(card_text, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        logger.error(f"Error fetching profile for {username}: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>خطا در دریافت پروفایل @{html.escape(username)}:</b>\n<code>{html.escape(str(e)[:150])}</code>",
            parse_mode="HTML",
        )


# =========================================================================
# Toggle Callbacks
# =========================================================================

@router.callback_query(F.data.startswith("prof:tog_"))
async def cb_toggle_option(callback: CallbackQuery):
    """Handle checkbox toggle buttons."""
    parts = callback.data.split(":")
    action = parts[1]
    username = parts[2]

    state_key = _get_state_key(callback.from_user.id, username)
    options = user_profile_states.get(state_key, ProfileFilterOptions())

    if action == "tog_v":
        options.include_videos = not options.include_videos
    elif action == "tog_p":
        options.include_photos = not options.include_photos
    elif action == "tog_g":
        options.include_gifs = not options.include_gifs
    elif action == "tog_rt":
        options.include_retweets = not options.include_retweets
    elif action == "tog_src":
        options.include_sourced_media = not options.include_sourced_media
    elif action == "tog_q":
        options.include_quotes = not options.include_quotes

    user_profile_states[state_key] = options
    new_markup = get_profile_settings_keyboard(username, options)

    await callback.message.edit_reply_markup(reply_markup=new_markup)
    await callback.answer()


@router.callback_query(F.data.startswith("prof:cycle_lim:"))
async def cb_cycle_limit(callback: CallbackQuery):
    """Cycle batch limit: 0 (All) -> 10 -> 25 -> 50 -> 100 -> 0."""
    username = callback.data.split(":")[2]
    state_key = _get_state_key(callback.from_user.id, username)
    options = user_profile_states.get(state_key, ProfileFilterOptions())

    limits = [0, 10, 25, 50, 100]
    curr_idx = limits.index(options.limit) if options.limit in limits else 0
    options.limit = limits[(curr_idx + 1) % len(limits)]

    user_profile_states[state_key] = options
    new_markup = get_profile_settings_keyboard(username, options)

    limit_desc = "♾️ همه (تا آخرین پست)" if options.limit == 0 else f"{options.limit} پست"
    await callback.message.edit_reply_markup(reply_markup=new_markup)
    await callback.answer(f"تعداد تنظیم شد روی: {limit_desc}")


@router.callback_query(F.data.startswith("prof:cancel:"))
async def cb_cancel_profile(callback: CallbackQuery):
    """Cancel and delete profile card."""
    await callback.message.delete()
    await callback.answer("عملیات لغو شد.")


# =========================================================================
# Batch Streaming Downloader Worker & Pinned Progress Delivery
# =========================================================================

async def _run_batch_download_task(
    bot, chat_id: int, user_id: int, username: str, options: ProfileFilterOptions, status_msg: Message, task_id: str, db: Database
):
    """Asynchronous worker that streamingly extracts, downloads, and delivers posts with pinned progress."""
    cancel_markup = get_cancel_batch_keyboard(task_id)

    # 1. Pin the progress message in the chat
    try:
        await bot.pin_chat_message(chat_id=chat_id, message_id=status_msg.message_id, disable_notification=True)
    except Exception as e:
        logger.debug(f"Could not pin status message: {e}")

    try:
        await status_msg.edit_text(
            f"🔍 <b>در حال آغاز استخراج خطی پست‌های @{html.escape(username)}...</b>\n\n"
            "⏳ <i>این پیام در بالای چت پین شده است تا وضعیت را لحظه‌ای مشاهده کنید.</i>",
            parse_mode="HTML",
            reply_markup=cancel_markup,
        )

        sent_post_count = 0
        total_media_count = 0
        video_count = 0
        photo_count = 0
        gif_count = 0

        # 2. Linear streaming extraction loop
        stream = profile_extractor.iter_profile_media_tweets_stream(username, options)

        async for tweet_item in stream:
            if task_id not in active_tasks or active_tasks[task_id].cancelled():
                logger.info(f"Batch task {task_id} was cancelled by user.")
                break

            # Update pinned progress before downloading item
            target_str = "♾️ همه پست‌های اکانت" if options.limit == 0 else f"{options.limit} پست"
            prog_text = (
                f"📥 <b>در حال دانلود و ارسال محتوای @{html.escape(username)}:</b>\n\n"
                f"📊 <b>پست‌های ارسال شده:</b> {sent_post_count} پست (هدف: {target_str})\n"
                f"⚡ <b>کل مدیاهای تحویل داده شده:</b> {total_media_count} فایل\n"
                f"  • 📹 ویدیوها: {video_count}  |  🖼️ عکس‌ها: {photo_count}  |  🎞️ گیف‌ها: {gif_count}\n\n"
                f"⏳ <b>وضعیت:</b> در حال دانلود پست شماره {sent_post_count + 1}..."
            )
            try:
                await status_msg.edit_text(prog_text, parse_mode="HTML", reply_markup=cancel_markup)
            except Exception:
                pass

            # Download post media to temporary disk directory
            temp_dir = bot_config.temp_download_dir / f"batch_{user_id}_{tweet_item.tweet_id}"
            post_result = await x2t.download_media_async(tweet_item.canonical_url, output_dir=temp_dir)

            if post_result.has_media:
                # Deliver to chat via MTProto (up to 2GB)
                await send_post_media(
                    bot=bot,
                    chat_id=chat_id,
                    result=post_result,
                )
                sent_post_count += 1
                total_media_count += post_result.media_count
                video_count += post_result.video_count
                photo_count += post_result.photo_count
                gif_count += post_result.gif_count

                # Record stats in DB
                await db.record_download(
                    user_id=user_id,
                    tweet_id=post_result.tweet_id,
                    media_count=post_result.media_count,
                )

            # Rate-limiting delay to protect Telegram bot
            await asyncio.sleep(1.5)

        # Final Completion
        if sent_post_count == 0:
            if not profile_extractor.has_auth_cookies():
                msg_text = (
                    f"⚠️ <b>هیچ پستی در اکانت @{html.escape(username)} یافت نشد.</b>\n\n"
                    "🔞 <b>علت احتمالی (محدودیت سنی / NSFW):</b>\n"
                    "این اکانت در توییتر دارای برچسب محتوای حساس یا بزرگسال است و توییتر مرور تایم‌لاین آن را برای کاربران مهمان (Guest) مسدود کرده است.\n\n"
                    "💡 <b>راه‌حل:</b> ادمین می‌تواند با دستور <code>/set_cookie</code> کوکی توییتر را تنظیم کند."
                )
            else:
                msg_text = (
                    f"⚠️ <b>هیچ پستی با فیلترهای انتخابی شما در اکانت @{html.escape(username)} یافت نشد.</b>\n\n"
                    "💡 <i>ممکن است فیلترها خیلی سخت‌گیرانه باشند یا اکانت پست مدیا جدیدی نداشته باشد.</i>"
                )
            await status_msg.edit_text(msg_text, parse_mode="HTML")
        else:
            final_text = (
                f"✅ <b>دانلود و ارسال محتوای @{html.escape(username)} با موفقیت پایان یافت!</b>\n\n"
                f"📊 <b>مجموع کل پست‌های ارسالی:</b> {sent_post_count} پست\n"
                f"⚡ <b>مجموع کل فایل‌های مدیا:</b> {total_media_count} فایل\n"
                f"  • 📹 ویدیوها: {video_count} عدد\n"
                f"  • 🖼️ تصاویر: {photo_count} عدد\n"
                f"  • 🎞️ گیف‌ها: {gif_count} عدد\n\n"
                "🌟 <i>تمام فایل‌ها با بالاترین کیفیت ممکن و بدون محدودیت ارسال شدند.</i>"
            )
            await status_msg.edit_text(final_text, parse_mode="HTML")

    except asyncio.CancelledError:
        await status_msg.edit_text(
            f"🛑 <b>عملیات دانلود @{html.escape(username)} توسط شما متوقف شد.</b>\n\n"
            f"• پست‌های ارسال شده تا این لحظه: {sent_post_count} پست ({total_media_count} فایل مدیا)",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in streaming batch worker for {username}: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>خطا در پردازش دسته‌ای:</b>\n<code>{html.escape(str(e)[:150])}</code>",
            parse_mode="HTML",
        )
    finally:
        active_tasks.pop(task_id, None)


@router.callback_query(F.data.startswith("prof:start:"))
async def cb_start_batch_download(callback: CallbackQuery, db: Database):
    """Start batch streaming downloader task."""
    username = callback.data.split(":")[2]
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    state_key = _get_state_key(user_id, username)
    options = user_profile_states.get(state_key, ProfileFilterOptions())

    task_id = str(uuid.uuid4())[:8]

    task = asyncio.create_task(
        _run_batch_download_task(
            bot=callback.bot,
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            options=options,
            status_msg=callback.message,
            task_id=task_id,
            db=db,
        )
    )
    active_tasks[task_id] = task
    await callback.answer("🚀 پردازش و دانلود خطی آغاز شد...")


@router.callback_query(F.data.startswith("prof:stop_task:"))
async def cb_stop_batch_task(callback: CallbackQuery):
    """Cancel running batch download task."""
    task_id = callback.data.split(":")[2]
    task = active_tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        await callback.answer("🛑 در حال توقف عملیات...")
    else:
        await callback.answer("عملیات قبلاً به پایان رسیده است.")
