"""Anti-flood / Rate limiting middleware for Telegram messages."""

import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from x2t.bot.config import bot_config


class ThrottlingMiddleware(BaseMiddleware):
    """Prevents spam by enforcing a minimum interval between requests per user."""

    def __init__(self, limit: float = bot_config.rate_limit_seconds):
        self.limit = limit
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        if user_id in self.user_timestamps:
            delta = now - self.user_timestamps[user_id]
            if delta < self.limit:
                # User sent message too fast
                # Silently ignore or answer if it is a command/link
                if event.text and ("x.com" in event.text or "twitter.com" in event.text):
                    await event.reply("⚠️ لطفاً کمی صبر کنید و درخواست‌ها را پشت سر هم ارسال نکنید.")
                return

        self.user_timestamps[user_id] = now
        return await handler(event, data)
