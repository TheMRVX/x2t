"""Handlers registration."""

from aiogram import Router
from x2t.bot.handlers.admin import router as admin_router
from x2t.bot.handlers.downloader import router as downloader_router
from x2t.bot.handlers.start import router as start_router


def setup_routers() -> Router:
    """Setup and include all bot routers in proper priority order."""
    main_router = Router(name="main_bot_router")
    main_router.include_router(admin_router)
    main_router.include_router(start_router)
    main_router.include_router(downloader_router)
    return main_router
