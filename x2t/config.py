"""Configuration settings for x2t."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Global configuration settings for x2t."""

    # Storage paths
    default_download_dir: Path = Field(
        default=Path("./downloads"),
        description="Default directory for saving downloaded media files",
    )

    # Network settings
    request_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for HTTP requests",
    )
    max_concurrent_downloads: int = Field(
        default=4,
        description="Max concurrent file downloads for multi-media tweets",
    )
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        description="Default User-Agent string for HTTP requests",
    )

    # yt-dlp specific options
    ytdlp_quiet: bool = True
    ytdlp_no_warnings: bool = True
    cookies_file: Optional[str] = None


# Global default configuration instance
config = Settings()
