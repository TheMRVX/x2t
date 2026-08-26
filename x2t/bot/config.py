"""Configuration settings for x2t Telegram Bot."""

import json
from pathlib import Path
from typing import Any, List, Optional
from pydantic import Field, field_validator
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
    api_id: Optional[int] = Field(
        default=None,
        description="Telegram App api_id from my.telegram.org (enables MTProto 2GB uploads)",
    )
    api_hash: Optional[str] = Field(
        default=None,
        description="Telegram App api_hash from my.telegram.org",
    )
    is_private: bool = Field(
        default=True,
        description="If True, only admin_ids and allowed_user_ids can use the bot",
    )
    admin_ids: Any = Field(
        default_factory=list,
        description="List of Telegram User IDs with admin access",
    )
    allowed_user_ids: Any = Field(
        default_factory=list,
        description="List of authorized Telegram user IDs when in private mode",
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
        default=2000,
        description="Max file size in MB supported (2000 MB with MTProto)",
    )
    twitter_auth_token: Optional[str] = Field(
        default=None,
        description="Twitter auth_token cookie for age-restricted accounts",
    )
    twitter_ct0: Optional[str] = Field(
        default=None,
        description="Twitter ct0 CSRF token",
    )
    clean_caption: bool = Field(
        default=False,
        description="If True, sends only raw post text without author, footer, or link buttons",
    )

    @field_validator("admin_ids", "allowed_user_ids", mode="before")
    @classmethod
    def parse_user_ids_list(cls, v: Any) -> List[int]:
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, (list, tuple, set)):
            return [int(x) for x in v if str(x).isdigit() or isinstance(x, (int, float))]
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                return []
            if clean.startswith("[") and clean.endswith("]"):
                try:
                    return [int(x) for x in json.loads(clean)]
                except Exception:
                    pass
            parts = clean.replace(",", " ").split()
            return [int(p) for p in parts if p.isdigit()]
        return []

    @property
    def has_mtproto(self) -> bool:
        """True if MTProto credentials are fully configured."""
        return bool(self.api_id and self.api_hash)


bot_config = BotSettings()
