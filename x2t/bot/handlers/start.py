"""Start, Help, About, and User History command handlers."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from x2t.bot.database.db import Database
from x2t.bot.keyboards.inline import get_back_keyboard, get_start_keyboard

router = Router(name="start_router")

START_TEXT = (
    "👋 <b>سلام! به ربات دانلودر توییتر (x2t) خوش آمدید.</b>\n\n"
    "🚀 <b>امکانات ربات:</b>\n"
    "• دانلود تمام ویدیوها و گیف‌های یک پست با <b>بالاترین کیفیت</b> (تا 4 ویدیو)\n"
    "• دانلود عکس‌ها و گالری‌های چندتایی با <b>کیفیت اصلی (Original)</b>\n"
    "• دانلود و استخراج کامل تایم‌لاین پروفایل‌ها (با ارسال نام کاربری @username)\n"
    "• تبدیل خودکار گیف‌ها به انیمیشن استاندارد تلگرام\n"
    "• ارسال در قالب آلبوم منظم (MediaGroup)\n\n"
    "📌 <b>نحوه استفاده:</b>\n"
    "فقط کافیست <b>لینک هر پست توییتر یا X</b> یا <b>آیدی پروفایل (@username)</b> را برای ربات ارسال کنید!"
)

HELP_TEXT = (
    "📖 <b>راهنمای استفاده از ربات:</b>\n\n"
    "1️⃣ وارد برنامه یا سایت Twitter / X شوید.\n"
    "2️⃣ روی دکمه Share (اشتراک‌گذاری) پست مورد نظر بزنید و <b>Copy Link</b> را انتخاب کنید.\n"
    "3️⃣ لینک کپی‌شده را در این ربات ارسال کنید.\n\n"
    "⚡ <b>دستورات کاربردی:</b>\n"
    "• <code>/history</code> - مشاهده تاریخچه آخرین پست‌های دانلود شده توسط شما\n"
    "• <code>/about</code> - اطلاعات و مشخصات فنی موتور x2t\n"
    "• ارسال <code>@username</code> - باز کردن پنل فیلتر و دانلود دسته‌ای کل رسانه‌های یک اکانت\n\n"
    "💡 <i>پست‌هایی که شامل ۲ تا ۴ مدیا باشند به صورت آلبوم کامل برای شما ارسال می‌شوند.</i>"
)

ABOUT_TEXT = (
    "ℹ️ <b>درباره پروژه x2t:</b>\n\n"
    "این ربات با موتور اختصاصی و متن‌باز <b>x2t</b> بدون وابستگی به هیچ وب‌سرویس واسطه یا پولی، "
    "مدیاها را مستقیماً با بالاترین کیفیت از سرورهای CDN استخراج و تحویل می‌دهد.\n\n"
    "⚡ مجهز به کش هوشمند درون‌حافظه‌ای و سیستم آپلود موازی MTProto."
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply(START_TEXT, parse_mode="HTML", reply_markup=get_start_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(HELP_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())


@router.message(Command("about"))
async def cmd_about(message: Message):
    await message.reply(ABOUT_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())


@router.message(Command("history"))
async def cmd_history(message: Message, db: Database):
    """Display latest 5 downloaded tweets for the current user."""
    user_id = message.from_user.id if message.from_user else 0
    history = await db.get_user_history(user_id=user_id, limit=5)

    if not history:
        await message.reply(
            "📜 <b>تاریخچه دانلودهای شما:</b>\n\n"
            "هنوز هیچ فایلی توسط شما دانلود نشده است!\n"
            "برای شروع، لینک یک پست توییتر را ارسال کنید.",
            parse_mode="HTML",
        )
        return

    text = "📜 <b>آخرین دانلودهای شما در ربات:</b>\n\n"
    for idx, item in enumerate(history, start=1):
        tweet_id = item["tweet_id"]
        count = item["media_count"]
        ts = item["timestamp"]
        url = f"https://x.com/i/status/{tweet_id}"
        text += f"{idx}. 🔗 <a href=\"{url}\">توییت {tweet_id}</a> ({count} مدیا) — <i>{ts}</i>\n"

    text += "\n💡 <i>روی هر لینک کلیک کنید تا توییت اصلی در توییتر باز شود.</i>"
    await message.reply(text, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "history_btn")
async def cb_history(callback: CallbackQuery, db: Database):
    user_id = callback.from_user.id if callback.from_user else 0
    history = await db.get_user_history(user_id=user_id, limit=5)

    if not history:
        await callback.message.edit_text(
            "📜 <b>تاریخچه دانلودهای شما:</b>\n\n"
            "هنوز هیچ فایلی توسط شما دانلود نشده است!\n"
            "برای شروع، لینک یک پست توییتر را ارسال کنید.",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(),
        )
        await callback.answer()
        return

    text = "📜 <b>آخرین دانلودهای شما در ربات:</b>\n\n"
    for idx, item in enumerate(history, start=1):
        tweet_id = item["tweet_id"]
        count = item["media_count"]
        ts = item["timestamp"]
        url = f"https://x.com/i/status/{tweet_id}"
        text += f"{idx}. 🔗 <a href=\"{url}\">توییت {tweet_id}</a> ({count} مدیا) — <i>{ts}</i>\n"

    text += "\n💡 <i>روی هر لینک کلیک کنید تا توییت اصلی در توییتر باز شود.</i>"
    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(HELP_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.edit_text(ABOUT_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "start_menu")
async def cb_start_menu(callback: CallbackQuery):
    await callback.message.edit_text(START_TEXT, parse_mode="HTML", reply_markup=get_start_keyboard())
    await callback.answer()
