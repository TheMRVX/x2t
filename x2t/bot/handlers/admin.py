"""Admin commands and management handlers."""

import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.core.profile_extractor import profile_extractor

router = Router(name="admin_router")


def is_admin(user_id: int) -> bool:
    """Check if user ID is in configured admin list."""
    return user_id in bot_config.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database):
    """Display overall bot stats to admin."""
    if not is_admin(message.from_user.id):
        return

    stats = await db.get_stats()
    text = (
        "📊 <b>آمار سیستم ربات x2t:</b>\n\n"
        f"👥 <b>تعداد کل کاربران:</b> {stats['total_users']:,}\n"
        f"📥 <b>تعداد کل فایل‌های دانلود شده:</b> {stats['total_downloads']:,}\n"
        f"⚡ <b>کاربران فعال ۲۴ ساعت گذشته:</b> {stats['active_24h']:,}"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("set_cookie"))
async def cmd_set_cookie(message: Message):
    """Set Twitter auth_token and ct0 cookies dynamically for NSFW/18+ accounts."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply(
            "⚠️ <b>نحوه استفاده از دستور تنظیم کوکی توییتر:</b>\n\n"
            "<code>/set_cookie YOUR_AUTH_TOKEN [YOUR_CT0]</code>\n\n"
            "💡 <i>با تنظیم auth_token، تمام اکانت‌های حساس (NSFW) و دارای محدودیت سنی بدون هیچ مشکلی باز می‌شوند.</i>",
            parse_mode="HTML",
        )
        return

    auth_token = parts[1].strip()
    ct0 = parts[2].strip() if len(parts) > 2 else None

    profile_extractor.set_twitter_auth_token(auth_token, ct0)
    await message.reply(
        "✅ <b>کوکی‌های توییتر با موفقیت در سیستم تنظیم شدند!</b>\n\n"
        "اکنون تایم‌لاین تمام اکانت‌های محدودشده و حساس (NSFW) نیز قابل دانلود است.",
        parse_mode="HTML",
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db: Database):
    """Broadcast announcement message to all users."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("⚠️ لطفاً متن پیام همگانی را بعد از دستور بنویسید:\n<code>/broadcast متن پیام</code>", parse_mode="HTML")
        return

    broadcast_text = parts[1]
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)

    status_msg = await message.reply(f"📢 ارسال پیام همگانی به {total} کاربر آغاز شد...")

    success = 0
    failed = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(chat_id=uid, text=broadcast_text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>ارسال همگانی پایان یافت.</b>\n\n"
        f"• موفق: {success}\n"
        f"• ناموفق (بلاک/حذف): {failed}",
        parse_mode="HTML",
    )
