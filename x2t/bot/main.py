"""Entry point for x2t Telegram Bot."""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.bot.handlers import setup_routers
from x2t.bot.middlewares import AccessControlMiddleware, ThrottlingMiddleware, UserTrackerMiddleware
from x2t.bot.services.mtproto_client import mtproto_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("x2t.bot")


async def setup_bot_commands(bot: Bot):
    """Register menu commands list with Telegram API (displayed next to keyboard)."""
    commands = [
        BotCommand(command="start", description="🚀 شروع به کار و راهنمای ربات"),
        BotCommand(command="help", description="📖 راهنمای کامل استفاده و فیلترها"),
        BotCommand(command="about", description="ℹ️ درباره سیستم و موتور دانلود x2t"),
        BotCommand(command="mode", description="⚙️ مشاهده و تغییر حالت خصوصی/عمومی (ادمین)"),
        BotCommand(command="stats", description="📊 آمار دانلودها و کاربران فعال (ادمین)"),
        BotCommand(command="allow", description="✅ افزودن کاربر به لیست مجاز (ادمین)"),
        BotCommand(command="disallow", description="🚫 لغو دسترسی کاربر (ادمین)"),
        BotCommand(command="set_cookie", description="🍪 تنظیم کوکی توییتر برای اکانت‌های حساس (ادمین)"),
        BotCommand(command="broadcast", description="📢 ارسال پیام همگانی (ادمین)"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot menu commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register bot menu commands: {e}")


async def main():
    """Main application lifecycle."""
    if not bot_config.bot_token:
        logger.error(
            "\n[ERROR] Telegram BOT_TOKEN is required.\n"
            "Please create a .env file with your token:\n"
            "BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuvWXyz\n"
        )
        sys.exit(1)

    logger.info("Initializing x2t Telegram Bot...")

    # 1. Initialize Database
    db = Database(db_path=bot_config.db_path)
    await db.init_db()
    logger.info(f"Database initialized at {bot_config.db_path}")

    # 2. Ensure temp directory exists
    bot_config.temp_download_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load Twitter Auth Token if configured
    if bot_config.twitter_auth_token:
        from x2t.core.profile_extractor import profile_extractor
        profile_extractor.set_twitter_auth_token(bot_config.twitter_auth_token, bot_config.twitter_ct0)
        logger.info("Configured Twitter auth_token from settings.")

    # 4. Start MTProto Client for 2GB uploads if api_id/api_hash configured
    if bot_config.has_mtproto:
        try:
            await mtproto_client.start()
        except Exception as e:
            logger.warning(f"Could not start MTProto client: {e}. Running in standard Bot API mode.")

    # 5. Create Bot and Dispatcher
    bot = Bot(
        token=bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 6. Register Bot Menu Commands Button
    await setup_bot_commands(bot)

    # 7. Register Middlewares (Outer middleware runs before all filters & routers)
    dp.update.outer_middleware(AccessControlMiddleware())
    dp.message.middleware(ThrottlingMiddleware(limit=bot_config.rate_limit_seconds))
    dp.message.middleware(UserTrackerMiddleware(db=db))
    dp.callback_query.middleware(UserTrackerMiddleware(db=db))

    # 8. Register Routers
    dp.include_router(setup_routers())

    # 9. Start Polling
    logger.info("Starting bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await mtproto_client.stop()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
