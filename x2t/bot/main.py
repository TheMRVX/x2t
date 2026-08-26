"""Entry point for x2t Telegram Bot with resilient logging, persistent SQLite, and token health monitoring."""

import asyncio
import os
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    MenuButtonCommands,
)

from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.bot.handlers import setup_routers
from x2t.bot.middlewares import (
    AccessControlMiddleware,
    ThrottlingMiddleware,
    UserTrackerMiddleware,
    error_router,
)
from x2t.bot.services.mtproto_client import mtproto_client
from x2t.core.profile_extractor import profile_extractor
from x2t.logger import get_logger, setup_logging

# 1. Initialize Colorized & Sanitized Logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=Path("logs/x2t_bot.log"),
)
logger = get_logger("x2t.bot")


async def setup_bot_commands(bot: Bot):
    """Register menu commands list with Telegram API (displayed next to keyboard)."""
    commands = [
        BotCommand(command="start", description="🚀 شروع به کار و راهنمای ربات"),
        BotCommand(command="history", description="📜 مشاهده تاریخچه آخرین دانلودها"),
        BotCommand(command="help", description="📖 راهنمای کامل استفاده و فیلترها"),
        BotCommand(command="about", description="ℹ️ درباره سیستم و موتور دانلود x2t"),
        BotCommand(command="mode", description="⚙️ مشاهده و تغییر حالت خصوصی/عمومی (ادمین)"),
        BotCommand(command="caption", description="✍️ تغییر قالب کپشن (ساده یا کامل) (ادمین)"),
        BotCommand(command="stats", description="📊 آمار دانلودها و وضعیت توییتر (ادمین)"),
        BotCommand(command="allow", description="✅ افزودن کاربر به لیست مجاز (ادمین)"),
        BotCommand(command="disallow", description="🚫 لغو دسترسی کاربر (ادمین)"),
        BotCommand(command="set_cookie", description="🍪 تنظیم کوکی توییتر برای اکانت‌های حساس (ادمین)"),
        BotCommand(command="broadcast", description="📢 ارسال پیام همگانی (ادمین)"),
    ]
    try:
        # Register commands for all scopes
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
        # Force enable the standard Menu Button in Telegram clients
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Bot menu commands and MenuButtonCommands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register bot menu commands: {e}")


async def main():
    """Main application lifecycle."""
    if not bot_config.bot_token:
        logger.error("BOT_TOKEN is required. Please set BOT_TOKEN in your environment or .env file.")
        sys.exit(1)

    logger.info("Initializing x2t Telegram Bot...")

    # 1. Initialize Database with persistent connection and WAL mode
    db = Database(db_path=bot_config.db_path)
    await db.init_db()
    logger.info(f"Database initialized at {bot_config.db_path} (WAL mode enabled)")

    # 2. Ensure temp and logs directories exist
    bot_config.temp_download_dir.mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # 3. Load dynamic settings from DB (if previously customized by admin)
    saved_mode = await db.get_setting("is_private")
    if saved_mode is not None:
        bot_config.is_private = (saved_mode.lower() == "true")
        logger.info(f"Loaded persistent bot mode from DB: is_private={bot_config.is_private}")

    saved_caption = await db.get_setting("clean_caption")
    if saved_caption is not None:
        bot_config.clean_caption = (saved_caption.lower() == "true")
        logger.info(f"Loaded persistent clean_caption from DB: {bot_config.clean_caption}")

    saved_allowed = await db.get_setting("allowed_user_ids")
    if saved_allowed:
        try:
            import json
            loaded_ids = json.loads(saved_allowed)
            for uid in loaded_ids:
                if uid not in bot_config.allowed_user_ids:
                    bot_config.allowed_user_ids.append(uid)
            logger.info(f"Loaded persistent allowed_user_ids from DB: {bot_config.allowed_user_ids}")
        except Exception as e:
            logger.warning(f"Failed to load allowed_user_ids from DB: {e}")

    saved_token = await db.get_setting("twitter_auth_token")
    saved_ct0 = await db.get_setting("twitter_ct0")
    if saved_token:
        profile_extractor.set_twitter_auth_token(saved_token, saved_ct0)
        logger.info("Loaded Twitter auth_token from persistent DB settings.")
    elif bot_config.twitter_auth_token:
        profile_extractor.set_twitter_auth_token(bot_config.twitter_auth_token, bot_config.twitter_ct0)
        logger.info("Configured Twitter auth_token from environment settings.")

    # 4. Check and log Twitter session health status
    _, health_msg = profile_extractor.check_auth_token_health()
    logger.info(f"Twitter session health check: {health_msg}")

    # 5. Start MTProto Client for 2GB uploads if api_id/api_hash configured
    if bot_config.has_mtproto:
        await mtproto_client.start()

    # 6. Create Bot and Dispatcher
    bot = Bot(
        token=bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 7. Register Bot Menu Commands Button
    await setup_bot_commands(bot)

    # 8. Register Middlewares
    dp.update.outer_middleware(AccessControlMiddleware())
    dp.message.middleware(ThrottlingMiddleware(limit=bot_config.rate_limit_seconds))
    dp.message.middleware(UserTrackerMiddleware(db=db))
    dp.callback_query.middleware(UserTrackerMiddleware(db=db))

    # 9. Register Routers and Global Error Boundary
    dp.include_router(setup_routers())
    dp.include_router(error_router)

    # 10. Start Polling
    logger.info("Starting bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await mtproto_client.stop()
        await bot.session.close()
        await db.close()
        logger.info("Bot stopped cleanly and database connections closed.")


if __name__ == "__main__":
    asyncio.run(main())
