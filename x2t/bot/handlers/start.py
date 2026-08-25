"""Start, Help, and About command handlers."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from x2t.bot.keyboards.inline import get_back_keyboard, get_start_keyboard

router = Router(name="start_router")

START_TEXT = (
    "👋 <b>سلام! به ربات دانلودر توییتر (x2t) خوش آمدید.</b>\n\n"
    "🚀 <b>امکانات ربات:</b>\n"
    "• دانلود تمام ویدیوها و گیف‌های یک پست با <b>بالاترین کیفیت</b> (تا 4 ویدیو)\n"
    "• دانلود عکس‌ها و گالری‌های چندتایی با <b>کیفیت اصلی (Original)</b>\n"
    "• تبدیل خودکار گیف‌ها به انیمیشن استاندارد تلگرام\n"
    "• ارسال در قالب آلبوم منظم (MediaGroup)\n\n"
    "📌 <b>نحوه استفاده:</b>\n"
    "فقط کافیست <b>لینک هر پست توییتر یا X</b> را برای ربات ارسال کنید!"
)

HELP_TEXT = (
    "📖 <b>راهنمای استفاده از ربات:</b>\n\n"
    "1️⃣ وارد برنامه یا سایت Twitter / X شوید.\n"
    "2️⃣ روی دکمه Share (اشتراک‌گذاری) پست مورد نظر بزنید و <b>Copy Link</b> را انتخاب کنید.\n"
    "3️⃣ لینک کپی‌شده را در این ربات ارسال کنید.\n\n"
    "⚡ <b>پشتیبانی از انواع لینک‌ها:</b>\n"
    "• <code>https://x.com/username/status/123456...</code>\n"
    "• <code>https://twitter.com/username/status/123456...</code>\n"
    "• لینک‌های کوتاه و نسخه موبایل\n\n"
    "💡 <i>پست‌هایی که شامل ۲ تا ۴ مدیا باشند به صورت آلبوم کامل برای شما ارسال می‌شوند.</i>"
)

ABOUT_TEXT = (
    "ℹ️ <b>درباره پروژه x2t:</b>\n\n"
    "این ربات با موتور اختصاصی و متن‌باز <b>x2t</b> بدون وابستگی به هیچ وب‌سرویس واسطه یا پولی، "
    "مدیاها را مستقیماً با بالاترین کیفیت از سرورهای CDN استخراج و تحویل می‌دهد."
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
