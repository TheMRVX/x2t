"""Unit tests for centralized logging, credential sanitization, and domain exceptions."""

import logging
from x2t.exceptions import (
    AgeRestrictedError,
    NoMediaFoundError,
    PrivateTweetError,
    ProfileNotFoundError,
    TweetNotFoundError,
    TwitterRateLimitError,
    UnauthorizedAccessError,
    X2TError,
)
from x2t.logger import ColorFormatter, SensitiveDataFilter, setup_logging


def test_sensitive_data_filter_masks_credentials():
    """Verify that sensitive tokens and credentials are redacted from logs."""
    filter_obj = SensitiveDataFilter()

    # 1. Test Telegram Bot Token redaction (0-entropy dynamically constructed dummy token)
    dummy_bot = "1234567890:" + ("A" * 35)
    record1 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Connecting bot with token {dummy_bot} to telegram",
        args=(),
        exc_info=None,
    )
    filter_obj.filter(record1)
    assert "1234567890:AAA" not in record1.msg
    assert "[REDACTED_BOT_TOKEN]" in record1.msg

    # 2. Test Twitter auth_token redaction (0-entropy 40-char hex string: all 'a')
    dummy_auth = "a" * 40
    record2 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Setting cookie auth_token='{dummy_auth}' in session",
        args=(),
        exc_info=None,
    )
    filter_obj.filter(record2)
    assert dummy_auth not in record2.msg
    assert "[REDACTED_AUTH_TOKEN]" in record2.msg

    # 3. Test Telegram API hash redaction (0-entropy 32-char hex string: all 'b')
    dummy_hash = "b" * 32
    record3 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"API Hash configured: api_hash='{dummy_hash}'",
        args=(),
        exc_info=None,
    )
    filter_obj.filter(record3)
    assert dummy_hash not in record3.msg
    assert "[REDACTED_API_HASH]" in record3.msg


def test_color_formatter_output():
    """Verify that ColorFormatter formats components and levels with readable tags."""
    formatter = ColorFormatter()
    record = logging.LogRecord(
        name="x2t.bot.downloader",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Downloading media for tweet 123",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "INFO" in formatted
    assert "[bot.downloader]" in formatted
    assert "Downloading media for tweet 123" in formatted


def test_domain_exceptions_formatting():
    """Verify that domain exceptions generate informative, actionable Persian messages."""
    # 1. TweetNotFoundError
    e1 = TweetNotFoundError(tweet_id="1825123456789")
    t1 = e1.format_telegram_error()
    assert "پست مورد نظر یافت نشد" in t1
    assert "TWEET_NOT_FOUND" in t1

    # 2. PrivateTweetError
    e2 = PrivateTweetError()
    t2 = e2.format_telegram_error()
    assert "توییت خصوصی" in t2
    assert "PRIVATE_ACCOUNT" in t2

    # 3. AgeRestrictedError
    e3 = AgeRestrictedError()
    t3 = e3.format_telegram_error()
    assert "محدودیت سنی" in t3
    assert "/set_cookie" in t3
    assert "AGE_RESTRICTED" in t3

    # 4. NoMediaFoundError
    e4 = NoMediaFoundError()
    t4 = e4.format_telegram_error()
    assert "فاقد هرگونه فایل مدیا" in t4
    assert "NO_MEDIA_FOUND" in t4

    # 5. TwitterRateLimitError
    e5 = TwitterRateLimitError()
    t5 = e5.format_telegram_error()
    assert "Rate Limit" in t5
    assert "TWITTER_RATE_LIMIT" in t5

    # 6. UnauthorizedAccessError
    e6 = UnauthorizedAccessError(user_id=12345678)
    t6 = e6.format_telegram_error()
    assert "دسترسی غیرمجاز" in t6
    assert "12345678" in t6
    assert "ACCESS_DENIED" in t6


def test_setup_logging_initialization(tmp_path):
    """Verify setup_logging configures root logger without exceptions."""
    log_file = tmp_path / "test.log"
    setup_logging(log_level="DEBUG", log_file=log_file)
    logger = logging.getLogger("x2t.test")
    logger.info("Test log line")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test log line" in content
