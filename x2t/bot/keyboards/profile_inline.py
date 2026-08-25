"""Interactive toggle keyboards for Advanced Profile Mode."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from x2t.models import ProfileFilterOptions


def get_profile_settings_keyboard(username: str, options: ProfileFilterOptions) -> InlineKeyboardMarkup:
    """Generate dynamic inline keyboard with live status indicators."""
    v_icon = "✅" if options.include_videos else "❌"
    p_icon = "✅" if options.include_photos else "❌"
    g_icon = "✅" if options.include_gifs else "❌"
    rt_icon = "✅" if options.include_retweets else "❌"
    src_icon = "✅" if options.include_sourced_media else "❌"
    quote_icon = "✅" if options.include_quotes else "❌"

    buttons = [
        [
            InlineKeyboardButton(text=f"📹 ویدیوها: {v_icon}", callback_data=f"prof:tog_v:{username}"),
            InlineKeyboardButton(text=f"🖼️ عکس‌ها: {p_icon}", callback_data=f"prof:tog_p:{username}"),
        ],
        [
            InlineKeyboardButton(text=f"🎞️ گیف‌ها: {g_icon}", callback_data=f"prof:tog_g:{username}"),
            InlineKeyboardButton(text=f"🔁 ریتوییت‌ها: {rt_icon}", callback_data=f"prof:tog_rt:{username}"),
        ],
        [
            InlineKeyboardButton(text=f"🏷️ ویدیوی دیگران (From @...): {src_icon}", callback_data=f"prof:tog_src:{username}"),
        ],
        [
            InlineKeyboardButton(text=f"💬 توییت‌های نقل‌قول: {quote_icon}", callback_data=f"prof:tog_q:{username}"),
        ],
        [
            InlineKeyboardButton(text=f"🔢 تعداد دریافتی: [ {options.limit} پست ]", callback_data=f"prof:cycle_lim:{username}"),
        ],
        [
            InlineKeyboardButton(text="🚀 شروع دانلود و ارسال", callback_data=f"prof:start:{username}"),
            InlineKeyboardButton(text="❌ انصراف", callback_data=f"prof:cancel:{username}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_batch_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Keyboard shown during batch download with cancel button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛑 لغو عملیات دانلود", callback_data=f"prof:stop_task:{task_id}")
            ]
        ]
    )
