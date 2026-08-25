"""Unit tests for AccessControlMiddleware (Private / Public modes)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User
from x2t.bot.config import bot_config
from x2t.bot.middlewares.access_control import AccessControlMiddleware


@pytest.mark.asyncio
async def test_access_control_public_mode():
    middleware = AccessControlMiddleware()
    bot_config.is_private = False
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = []

    handler = AsyncMock(return_value="OK")
    event = MagicMock(spec=Message)
    event.from_user = MagicMock(spec=User, id=999)

    res = await middleware(handler, event, {})
    assert res == "OK"
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_access_control_private_mode_admin_allowed():
    middleware = AccessControlMiddleware()
    bot_config.is_private = True
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = []

    handler = AsyncMock(return_value="OK")
    event = MagicMock(spec=Message)
    event.from_user = MagicMock(spec=User, id=111)

    res = await middleware(handler, event, {})
    assert res == "OK"
    handler.assert_called_once()


@pytest.mark.asyncio
async def test_access_control_private_mode_unauthorized_blocked():
    middleware = AccessControlMiddleware()
    bot_config.is_private = True
    bot_config.admin_ids = [111]
    bot_config.allowed_user_ids = [222]

    handler = AsyncMock(return_value="OK")
    event = MagicMock(spec=Message)
    event.from_user = MagicMock(spec=User, id=999)
    event.reply = AsyncMock()

    res = await middleware(handler, event, {})
    assert res is None
    handler.assert_not_called()
    event.reply.assert_called_once()
