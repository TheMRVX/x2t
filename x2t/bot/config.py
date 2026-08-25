"""Configuration settings for x2t Telegram Bot."""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Bot configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(
        default="",
        description="Telegram Bot API Token from @BotFather",
    )
    admin_ids: List[int] = Field(
        default_factory=list,
        description="List of Telegram User IDs with admin access",
    )
    db_path: str = Field(
        default="bot_database.sqlite3",
        description="Path to SQLite database file",
    )
    temp_download_dir: Path = Field(
        default=Path("./downloads/temp_bot"),
        description="Temporary directory for downloaded media files before sending",
    )
    rate_limit_seconds: float = Field(
        default=2.0,
        description="Minimum seconds between requests per user (Anti-Flood)",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Max file size in MB supported by standard Telegram Bot API",
    )


bot_config = BotSettings()
