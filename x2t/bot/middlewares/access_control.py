"""Access control middleware to enforce Private or Public bot operation."""

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from x2t.bot.config import bot_config

logger = logging.getLogger("x2t.bot.access")


class AccessControlMiddleware(BaseMiddleware):
    """Enforces access control if bot is configured in private mode."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not bot_config.is_private:
            return await handler(event, data)

        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)

        user_id = from_user.id
        is_allowed = user_id in bot_config.admin_ids or user_id in bot_config.allowed_user_ids

        if not is_allowed:
            logger.warning(f"Unauthorized access attempt by user_id: {user_id} (@{from_user.username})")
            if isinstance(event, Message):
                await event.reply(
                    "⛔ <b>دسترسی غیرمجاز!</b>\n\n"
                    "این ربات در حالت <b>خصوصی (Private)</b> تنظیم شده است و تنها برای ادمین و کاربران مجاز در دسترس است.\n\n"
                    f"🆔 <b>شناسه عددی شما (User ID):</b> <code>{user_id}</code>\n"
                    "💡 <i>در صورت نیاز، این شناسه را به ادمین بدهید تا با دستور <code>/allow {user_id}</code> دسترسی شما را باز کند.</i>",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(f"⛔ دسترسی خصوصی است. شناسه شما: {user_id}", show_alert=True)
            return

        return await handler(event, data)
