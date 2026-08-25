"""Global error boundary middleware and exception router for Telegram Bot."""

import html
import uuid
from aiogram import Router
from aiogram.types import ErrorEvent, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from x2t.exceptions import X2TError
from x2t.logger import get_logger

logger = get_logger("x2t.bot.errors")
error_router = Router(name="error_boundary_router")


@error_router.errors()
async def global_error_handler(event: ErrorEvent):
    """Catch-all global error boundary for Aiogram updates."""
    exception = event.exception
    update = event.update
    incident_id = str(uuid.uuid4())[:8].upper()

    user_id = None
    chat_id = None
    original_message: Message = None

    if update.message:
        original_message = update.message
        user_id = update.message.from_user.id if update.message.from_user else None
        chat_id = update.message.chat.id
    elif update.callback_query:
        original_message = update.callback_query.message if isinstance(update.callback_query.message, Message) else None
        user_id = update.callback_query.from_user.id if update.callback_query.from_user else None
        chat_id = update.callback_query.message.chat.id if update.callback_query.message else None

    # Handle Known Domain Exceptions
    if isinstance(exception, X2TError):
        logger.warning(
            f"Handled X2TError [{exception.error_code}] for user={user_id} chat={chat_id}: {exception.message}"
        )
        if original_message:
            try:
                await original_message.reply(
                    exception.format_telegram_error(),
                    parse_mode="HTML",
                )
            except Exception as send_err:
                logger.error(f"Failed to deliver domain error message to user {user_id}: {send_err}")
        return True

    # Handle Telegram-Specific Errors
    if isinstance(exception, TelegramForbiddenError):
        logger.warning(f"Bot was blocked by user {user_id} or kicked from chat {chat_id}.")
        return True

    if isinstance(exception, TelegramBadRequest):
        logger.warning(f"TelegramBadRequest for user={user_id} chat={chat_id}: {exception}")
        if original_message:
            try:
                await original_message.reply(
                    f"⚠️ <b>خطای درخواست تلگرام:</b>\n<code>{html.escape(str(exception))}</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return True

    # Handle Unexpected / Unhandled Internal Errors
    logger.error(
        f"🚨 Unhandled exception [Incident #{incident_id}] for user={user_id} chat={chat_id}: {exception}",
        exc_info=True,
    )

    if original_message:
        friendly_text = (
            "❌ <b>خطای غیرمنتظره در پردازش!</b>\n\n"
            "متأسفانه در پردازش این درخواست خطایی رخ داد و گزارش آن برای تیم فنی ثبت گردید.\n\n"
            f"🔖 <code>کد پیگیری خطا: #{incident_id}</code>\n"
            "💡 <i>لطفاً چند دقیقه دیگر مجدداً تلاش فرمایید.</i>"
        )
        try:
            await original_message.reply(friendly_text, parse_mode="HTML")
        except Exception as send_err:
            logger.error(f"Could not send incident report to user {user_id}: {send_err}")

    return True
