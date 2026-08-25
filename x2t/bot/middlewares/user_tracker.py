"""Middleware to register and track user activity in database."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from x2t.bot.database.db import Database


class UserTrackerMiddleware(BaseMiddleware):
    """Tracks active users and ensures they are recorded in the database."""

    def __init__(self, db: Database):
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db

        user: User = data.get("event_from_user")
        if user and not user.is_bot:
            await self.db.upsert_user(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
            )

        return await handler(event, data)
