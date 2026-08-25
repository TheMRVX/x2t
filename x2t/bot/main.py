"""Entry point for x2t Telegram Bot."""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from x2t.bot.config import bot_config
from x2t.bot.database.db import Database
from x2t.bot.handlers import setup_routers
from x2t.bot.middlewares import ThrottlingMiddleware, UserTrackerMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("x2t.bot")


async def main():
    """Start polling loop for x2t Telegram Bot."""
    if not bot_config.bot_token:
        logger.error("BOT_TOKEN is not set in environment or .env file!")
        print(
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

    # 3. Create Bot and Dispatcher
    bot = Bot(
        token=bot_config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 4. Register Middlewares
    dp.message.middleware(ThrottlingMiddleware(limit=bot_config.rate_limit_seconds))
    dp.message.middleware(UserTrackerMiddleware(db=db))
    dp.callback_query.middleware(UserTrackerMiddleware(db=db))

    # 5. Register Routers
    dp.include_router(setup_routers())

    # 6. Start Polling
    logger.info("Starting bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
