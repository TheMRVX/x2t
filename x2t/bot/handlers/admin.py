"""Admin commands and management handlers with persistent settings, allowed users, and token health checks."""

import asyncio
import json
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
    """Display overall bot stats and Twitter session health to admin."""
    if not is_admin(message.from_user.id):
        return

    stats = await db.get_stats()
    mode_str = "🔒 خصوصی (Private)" if bot_config.is_private else "🌐 عمومی (Public)"
    _, health_str = profile_extractor.check_auth_token_health()

    text = (
        "📊 <b>آمار سیستم ربات x2t:</b>\n\n"
        f"⚙️ <b>وضعیت دسترسی ربات:</b> {mode_str}\n"
        f"👥 <b>تعداد کل کاربران:</b> {stats['total_users']:,}\n"
        f"📥 <b>تعداد کل فایل‌های دانلود شده:</b> {stats['total_downloads']:,}\n"
        f"⚡ <b>کاربران فعال ۲۴ ساعت گذشته:</b> {stats['active_24h']:,}\n"
        f"📋 <b>تعداد کاربران مجاز:</b> {len(bot_config.allowed_user_ids)}\n\n"
        f"🍪 <b>وضعیت نشست توییتر (Auth Token):</b>\n{health_str}"
    )
    await message.reply(text, parse_mode="HTML")


@router.message(Command("mode"))
async def cmd_mode(message: Message, db: Database):
    """Toggle or show Public/Private access mode and persist in DB."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        curr_mode = "🔒 خصوصی (Private)" if bot_config.is_private else "🌐 عمومی (Public)"
        await message.reply(
            f"⚙️ <b>حالت فعلی ربات:</b> {curr_mode}\n\n"
            "💡 برای تغییر حالت می‌توانید از دستورات زیر استفاده کنید:\n"
            "• <code>/mode private</code> (فقط ادمین‌ها و کاربران مجاز)\n"
            "• <code>/mode public</code> (دسترسی آزاد برای همه)",
            parse_mode="HTML",
        )
        return

    target_mode = parts[1].lower()
    if target_mode in ("private", "priv", "close", "off"):
        bot_config.is_private = True
        await db.set_setting("is_private", "true")
        await message.reply("🔒 <b>حالت ربات به «خصوصی (Private)» تغییر یافت.</b>\nتنظیمات در پایگاه داده ذخیره شد.", parse_mode="HTML")
    elif target_mode in ("public", "pub", "open", "on"):
        bot_config.is_private = False
        await db.set_setting("is_private", "false")
        await message.reply("🌐 <b>حالت ربات به «عمومی (Public)» تغییر یافت.</b>\nتنظیمات در پایگاه داده ذخیره شد.", parse_mode="HTML")
    else:
        await message.reply("⚠️ لطفاً <code>/mode private</code> یا <code>/mode public</code> را وارد کنید.", parse_mode="HTML")


@router.message(Command("allow"))
async def cmd_allow_user(message: Message, db: Database):
    """Authorize a specific user ID in private mode and persist in database."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("⚠️ فرمت دستور:\n<code>/allow USER_ID</code>", parse_mode="HTML")
        return

    target_uid = int(parts[1])
    if target_uid not in bot_config.allowed_user_ids:
        bot_config.allowed_user_ids.append(target_uid)
        await db.set_setting("allowed_user_ids", json.dumps(bot_config.allowed_user_ids))

    await message.reply(f"✅ کاربر با شناسه <code>{target_uid}</code> به لیست کاربران مجاز اضافه شد.", parse_mode="HTML")


@router.message(Command("disallow"))
async def cmd_disallow_user(message: Message, db: Database):
    """Revoke authorization for a user ID in private mode and persist in database."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("⚠️ فرمت دستور:\n<code>/disallow USER_ID</code>", parse_mode="HTML")
        return

    target_uid = int(parts[1])
    if target_uid in bot_config.allowed_user_ids:
        bot_config.allowed_user_ids.remove(target_uid)
        await db.set_setting("allowed_user_ids", json.dumps(bot_config.allowed_user_ids))

    await message.reply(f"🚫 دسترسی کاربر با شناسه <code>{target_uid}</code> لغو شد.", parse_mode="HTML")


@router.message(Command("set_cookie"))
async def cmd_set_cookie(message: Message, db: Database):
    """Set Twitter auth_token and ct0 cookies dynamically for NSFW/18+ accounts with persistence."""
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
    await db.set_setting("twitter_auth_token", auth_token)
    if ct0:
        await db.set_setting("twitter_ct0", ct0)

    is_valid, health_msg = profile_extractor.check_auth_token_health()
    await message.reply(
        "✅ <b>کوکی‌های توییتر با موفقیت تنظیم و ذخیره شدند!</b>\n\n"
        f"📊 <b>وضعیت اعتبارسنجی:</b> {health_msg}",
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
