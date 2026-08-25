"""Data models for x2t media extraction and downloader."""

from enum import Enum
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "animated_gif"


class MediaItem(BaseModel):
    """Represents a single media element (photo, video, or animated gif) extracted from a post."""

    id: str = Field(description="Unique identifier or index of the media item within the tweet")
    type: MediaType = Field(description="Type of media (photo, video, animated_gif)")
    url: str = Field(description="Direct download or streaming URL")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    bitrate: Optional[int] = Field(default=None, description="Bitrate in bps (for videos)")
    duration_seconds: Optional[float] = Field(default=None, description="Duration in seconds (for videos)")
    thumbnail_url: Optional[str] = Field(default=None, description="Preview / thumbnail image URL")
    local_path: Optional[str] = Field(default=None, description="Local absolute filepath if downloaded")
    filename: Optional[str] = Field(default=None, description="Filename on disk")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes if known/downloaded")
    is_gif: bool = Field(default=False, description="True if Twitter marked this as an animated GIF")

    @computed_field
    @property
    def resolution(self) -> Optional[str]:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None

    @computed_field
    @property
    def is_downloaded(self) -> bool:
        return bool(self.local_path and Path(self.local_path).exists())


class PostMediaResult(BaseModel):
    """Represents all extracted media and metadata for a single Twitter/X post."""

    tweet_id: str = Field(description="Numeric ID of the tweet")
    original_url: str = Field(description="Original URL provided by user")
    canonical_url: str = Field(description="Canonical https://x.com/user/status/id URL")
    text: Optional[str] = Field(default=None, description="Tweet text content")
    author_name: Optional[str] = Field(default=None, description="Display name of the author")
    author_username: Optional[str] = Field(default=None, description="Twitter handle without @")
    items: List[MediaItem] = Field(default_factory=list, description="List of media items (up to 4)")
    created_at: Optional[str] = Field(default=None, description="Tweet timestamp")

    @computed_field
    @property
    def media_count(self) -> int:
        return len(self.items)

    @computed_field
    @property
    def has_media(self) -> bool:
        return len(self.items) > 0

    @computed_field
    @property
    def video_count(self) -> int:
        return sum(1 for item in self.items if item.type == MediaType.VIDEO)

    @computed_field
    @property
    def photo_count(self) -> int:
        return sum(1 for item in self.items if item.type == MediaType.PHOTO)

    @computed_field
    @property
    def gif_count(self) -> int:
        return sum(1 for item in self.items if item.type == MediaType.GIF)
