"""Unit tests for AccessControlMiddleware (Private / Public modes)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, Update, User
from x2t.bot.config import bot_config
from x2t.bot.middlewares.access_control import AccessControlMiddleware


@pytest.mark.asyncio
async def test_access_control_public_mode():
    middleware = AccessControlMiddleware()
    bot_config.is_private = False
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = []

    handler = AsyncMock(return_value="OK")
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User, id=999, username="random_user", full_name="Random")
    update = MagicMock(spec=Update, message=msg, callback_query=None, edited_message=None)

    res = await middleware(handler, update, {})
    assert res == "OK"
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_access_control_private_mode_admin_allowed():
    middleware = AccessControlMiddleware()
    bot_config.is_private = True
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = []

    handler = AsyncMock(return_value="OK")
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User, id=111, username="admin_user", full_name="Admin")
    update = MagicMock(spec=Update, message=msg, callback_query=None, edited_message=None)

    res = await middleware(handler, update, {})
    assert res == "OK"
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_access_control_private_mode_unauthorized_blocked():
    middleware = AccessControlMiddleware()
    bot_config.is_private = True
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = [222]

    handler = AsyncMock(return_value="OK")
    msg = MagicMock(spec=Message)
    msg.text = "/start"
    msg.from_user = MagicMock(spec=User, id=999, username="stranger", full_name="Stranger")
    msg.reply = AsyncMock()
    update = MagicMock(spec=Update, message=msg, callback_query=None, edited_message=None)

    res = await middleware(handler, update, {})
    assert res is None
    handler.assert_not_called()
    msg.reply.assert_called_once()


@pytest.mark.asyncio
async def test_access_control_ignores_bot_or_service_messages():
    """Verify that bot's own events, pins, and service updates are never blocked as unauthorized users."""
    middleware = AccessControlMiddleware()
    bot_config.is_private = True
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = []

    handler = AsyncMock(return_value="OK")
    # 1. Event from a bot (like bot itself 9999999999)
    bot_user = MagicMock(spec=User, id=9999999999, is_bot=True, username="my_bot")
    msg = MagicMock(spec=Message, from_user=bot_user)
    update = MagicMock(spec=Update, message=msg, callback_query=None, edited_message=None)

    res = await middleware(handler, update, {})
    assert res == "OK"
    handler.assert_called_once()
