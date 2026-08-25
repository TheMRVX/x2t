"""Inline keyboards for x2t Telegram Bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_tweet_keyboard(tweet_url: str) -> InlineKeyboardMarkup:
    """Create inline keyboard with link to original post."""
    buttons = [
        [
            InlineKeyboardButton(text="🔗 مشاهده پست در X", url=tweet_url),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Create main start menu keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="📖 راهنمای استفاده", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ درباره ربات", callback_data="about"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Create back button keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="start_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
