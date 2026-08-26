"""Centralized, colorized, and secure logging subsystem for x2t."""

import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Sanitizes sensitive credentials from log records (Bot tokens, Twitter auth cookies, API hashes)."""

    # Patterns for sensitive data
    PATTERNS = [
        # Telegram Bot Token (e.g. 123456789:ABCdefGhIJKlmNoPQRstuvWXyz)
        (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,45}\b"), "[REDACTED_BOT_TOKEN]"),
        # Twitter auth_token hex string (e.g. auth_token=abcdef0123456789abcdef0123456789abcdef01)
        (re.compile(r"(auth_token=['\"]?)[a-f0-9]{32,64}(['\"]?)", re.IGNORECASE), r"\1[REDACTED_AUTH_TOKEN]\2"),
        # Telegram API Hash (e.g. api_hash=abcdef0123456789abcdef0123456789)
        (re.compile(r"(api_hash=['\"]?)[a-f0-9]{32}(['\"]?)", re.IGNORECASE), r"\1[REDACTED_API_HASH]\2"),
        # Twitter ct0 token
        (re.compile(r"(ct0=['\"]?)[a-f0-9]{32,160}(['\"]?)", re.IGNORECASE), r"\1[REDACTED_CT0]\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, repl in self.PATTERNS:
                        arg = pattern.sub(repl, arg)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True


class ColorFormatter(logging.Formatter):
    """Terminal color formatter with icons and timestamps."""

    # ANSI Colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"

    LEVEL_COLORS = {
        logging.DEBUG: (DIM + CYAN, "🐞 DEBUG"),
        logging.INFO: (GREEN, "⚡ INFO "),
        logging.WARNING: (YELLOW, "⚠️ WARN "),
        logging.ERROR: (RED, "❌ ERROR"),
        logging.CRITICAL: (BOLD + RED, "🔥 CRIT "),
    }

    def format(self, record: logging.LogRecord) -> str:
        color, level_name = self.LEVEL_COLORS.get(record.levelno, (self.RESET, record.levelname))
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        component = record.name
        if component.startswith("x2t."):
            component = component[4:]  # Remove 'x2t.' prefix for cleaner terminal logs

        # Format: 2026-08-26 00:52:00 | ⚡ INFO  | [bot] Message
        header = f"{self.DIM}{time_str}{self.RESET} | {color}{level_name}{self.RESET} | {self.MAGENTA}[{component}]{self.RESET}"
        message = record.getMessage()

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{header} {message}\n{self.RED}{exc_text}{self.RESET}"
        return f"{header} {message}"


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
):
    """Configure structured, filtered, and colorized logging for entire application."""
    if not log_level:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    level = getattr(logging, log_level, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to prevent duplicate lines
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    sensitive_filter = SensitiveDataFilter()

    # 1. Console / Stderr Stream Handler (Immediate unbuffered terminal output)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColorFormatter())
    console_handler.addFilter(sensitive_filter)
    root_logger.addHandler(console_handler)

    # 2. File Handler (if requested or in ./logs)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

    # Suppress verbose noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("pyrogram.session.auth").setLevel(logging.WARNING)
    logging.getLogger("pyrogram.connection.connection").setLevel(logging.WARNING)
    logging.getLogger("pyrogram.session.session").setLevel(logging.WARNING)


def get_logger(name: str = "x2t") -> logging.Logger:
    """Get or create a named logger with proper hierarchy."""
    return logging.getLogger(name)
