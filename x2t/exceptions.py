"""Standardized domain exceptions and user-friendly error translations for x2t."""

from typing import Optional


class X2TError(Exception):
    """Base class for all x2t domain exceptions."""

    def __init__(
        self,
        message: str,
        user_friendly_message: Optional[str] = None,
        tip: Optional[str] = None,
        error_code: str = "X2T_GENERAL_ERROR",
    ):
        super().__init__(message)
        self.message = message
        self.user_friendly_message = user_friendly_message or (
            "❌ <b>خطایی در پردازش رخ داد.</b>\n"
            "لطفاً مجدداً تلاش کنید یا لینک ارسالی را بررسی فرمایید."
        )
        self.tip = tip
        self.error_code = error_code

    def format_telegram_error(self) -> str:
        """Format a clear, attractive Persian HTML message for Telegram users."""
        text = f"{self.user_friendly_message}\n"
        if self.tip:
            text += f"\n💡 <b>راهنما:</b> <i>{self.tip}</i>\n"
        text += f"\n🔖 <code>کد پیگیری: {self.error_code}</code>"
        return text


class ExtractionError(X2TError):
    """Base error for media extraction failures."""

    def __init__(
        self,
        message: str,
        user_friendly_message: Optional[str] = None,
        tip: Optional[str] = None,
        error_code: str = "EXTRACTION_FAILED",
    ):
        super().__init__(
            message=message,
            user_friendly_message=user_friendly_message or (
                "❌ <b>خطا در استخراج اطلاعات پست از توییتر (X).</b>\n"
                "سیستم نتوانست اطلاعات این پست را دریافت کند."
            ),
            tip=tip,
            error_code=error_code,
        )


class TweetNotFoundError(ExtractionError):
    """Tweet does not exist or has been deleted."""

    def __init__(self, message: str = "Tweet not found or deleted.", tweet_id: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=(
                "🔍 <b>پست مورد نظر یافت نشد!</b>\n\n"
                "این توییت ممکن است توسط نویسنده حذف شده باشد یا لینک ارسالی معتبر نباشد."
            ),
            tip="صحت لینک ارسالی را مجدداً بررسی کنید.",
            error_code="TWEET_NOT_FOUND",
        )
        self.tweet_id = tweet_id


class PrivateTweetError(ExtractionError):
    """Tweet is protected or belongs to a private account."""

    def __init__(self, message: str = "Tweet belongs to a protected account.", username: Optional[str] = None):
        super().__init__(
            message=message,
            user_friendly_message=(
                "🔒 <b>توییت خصوصی (Private / Protected)!</b>\n\n"
                "این پست متعلق به یک حساب کاربری خصوصی (قفل‌شده) در توییتر است و امکان دسترسی به مدیای آن بدون فالو کردن وجود ندارد."
            ),
            tip="فقط توییت‌های عمومی (Public) قابل دانلود هستند.",
            error_code="PRIVATE_ACCOUNT",
        )
        self.username = username


class AgeRestrictedError(ExtractionError):
    """Tweet or profile is age-restricted / NSFW."""

    def __init__(self, message: str = "Tweet is age-restricted or sensitive content."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "🔞 <b>محتوای حساس یا دارای محدودیت سنی (NSFW)!</b>\n\n"
                "توییتر دسترسی کاربران بدون لاگین (Guest) به این پست را به دلیل قوانین محتوای حساس مسدود کرده است."
            ),
            tip="ادمین می‌تواند با ارسال دستور /set_cookie و وارد کردن توکن حساب توییتر، دسترسی به محتوای بزرگسال را فعال کند.",
            error_code="AGE_RESTRICTED",
        )


class NoMediaFoundError(ExtractionError):
    """Tweet contains text only with no attached media."""

    def __init__(self, message: str = "Tweet contains no photo, video, or GIF."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "⚠️ <b>این توییت فاقد هرگونه فایل مدیا است!</b>\n\n"
                "پست ارسالی فقط شامل متن بوده و هیچ ویدیو، تصویر یا گیفی برای دانلود در آن وجود ندارد."
            ),
            tip="تنها پست‌های دارای مدیا قابل استخراج هستند.",
            error_code="NO_MEDIA_FOUND",
        )


class TwitterRateLimitError(ExtractionError):
    """Twitter API or Syndication returned 429 Too Many Requests."""

    def __init__(self, message: str = "Twitter rate limit reached."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "⏱️ <b>محدودیت موقت درخواست‌های توییتر (Rate Limit)!</b>\n\n"
                "تعداد زیادی درخواست در بازه زمانی کوتاه ارسال شده است و توییتر موقتاً پاسخگویی را کند کرده است."
            ),
            tip="لطفاً ۱ الی ۲ دقیقه دیگر مجدداً تلاش کنید.",
            error_code="TWITTER_RATE_LIMIT",
        )


class ProfileNotFoundError(ExtractionError):
    """Twitter profile does not exist or has been suspended."""

    def __init__(self, username: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Profile @{username} not found or suspended.",
            user_friendly_message=(
                f"👤 <b>پروفایل @{username} یافت نشد!</b>\n\n"
                "این نام کاربری وجود ندارد یا حساب کاربری آن در توییتر ساسپند/غیرفعال شده است."
            ),
            tip="از صحت آیدی کاربری اطمینان حاصل کنید.",
            error_code="PROFILE_NOT_FOUND",
        )
        self.username = username


class NetworkConnectionError(X2TError):
    """Network connection timeout, DNS failure, or proxy error."""

    def __init__(self, message: str = "Network connection failed."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "🌐 <b>خطا در برقراری ارتباط با سرور!</b>\n\n"
                "ارتباط شبکه ربات با سرورهای توییتر به دلیل قطعی اینترنت یا کندی پروکسی با تایم‌اوت مواجه شد."
            ),
            tip="لطفاً چند لحظه بعد مجدداً تلاش نمایید.",
            error_code="NETWORK_TIMEOUT",
        )


class MediaDownloadError(X2TError):
    """Failed to download media file chunks or FFmpeg conversion failed."""

    def __init__(self, message: str = "Failed to download media stream or file."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "📥 <b>خطا در دانلود یا پردازش فایل‌های مدیا!</b>\n\n"
                "در حین دریافت استریم یا تبدیل ویدیوی توییت مشکلی پیش آمد."
            ),
            tip="ممکن است لینک استریم منقضی شده باشد. مجدداً ارسال کنید.",
            error_code="DOWNLOAD_STREAM_ERROR",
        )


class TelegramDeliveryError(X2TError):
    """Failed to upload or deliver media to Telegram chat."""

    def __init__(self, message: str = "Failed to send media via Telegram API or MTProto."):
        super().__init__(
            message=message,
            user_friendly_message=(
                "🚀 <b>خطا در ارسال فایل به تلگرام!</b>\n\n"
                "فایل‌ها دانلود شدند اما تلگرام در تحویل بسته مدیا با خطا مواجه شد."
            ),
            tip="در صورت تکرار، حجم فایل یا اتصال چت را بررسی کنید.",
            error_code="TELEGRAM_DELIVERY_ERROR",
        )


class UnauthorizedAccessError(X2TError):
    """Unauthorized user tried accessing private bot."""

    def __init__(self, user_id: int):
        super().__init__(
            message=f"Access denied for user {user_id}",
            user_friendly_message=(
                "⛔ <b>دسترسی غیرمجاز!</b>\n\n"
                "این ربات در حالت خصوصی (Private) تنظیم شده است و تنها برای کاربران مجاز قابل استفاده می‌باشد.\n\n"
                f"🆔 <b>شناسه عددی شما (User ID):</b> <code>{user_id}</code>\n"
                "جهت دریافت دسترسی، این شناسه را برای ادمین ربات ارسال فرمایید."
            ),
            tip="برای دسترسی با مدیر ربات تماس بگیرید.",
            error_code="ACCESS_DENIED",
        )
        self.user_id = user_id
