"""Data models for x2t media extraction, profile scrapers, and downloader."""

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


# =========================================================================
# Advanced Profile Mode Models
# =========================================================================

class ProfileFilterOptions(BaseModel):
    """Filter options configured by user before downloading profile media."""

    include_videos: bool = Field(default=True, description="Download native video posts")
    include_photos: bool = Field(default=True, description="Download photo posts")
    include_gifs: bool = Field(default=True, description="Download animated GIF posts")
    include_retweets: bool = Field(default=False, description="Include reposts/retweets (Default: False)")
    include_sourced_media: bool = Field(default=False, description="Include media from other accounts 'From @other' (Default: False)")
    include_quotes: bool = Field(default=False, description="Include quote tweets (Default: False)")
    limit: int = Field(default=0, description="Max matching tweets to download (0 = Unlimited / All available)")


class ProfileInfo(BaseModel):
    """Metadata summary of a Twitter/X user profile."""

    rest_id: Optional[str] = Field(default=None, description="Numeric User ID")
    username: str = Field(description="Twitter handle without @")
    name: str = Field(description="Display name")
    bio: Optional[str] = Field(default=None, description="Account biography description")
    avatar_url: Optional[str] = Field(default=None, description="Profile avatar picture URL")
    followers_count: Optional[int] = Field(default=None, description="Followers count")
    media_count: Optional[int] = Field(default=None, description="Approximate total media count")


class ProfileTweetItem(BaseModel):
    """Represents a tweet discovered on a profile timeline with attribution flags."""

    tweet_id: str
    canonical_url: str
    text: Optional[str] = None
    created_at: Optional[str] = None
    is_retweet: bool = False
    is_quote: bool = False
    source_user: Optional[str] = None  # Attribution username e.g. "From @OriginalCreator"
    author_username: str
    author_name: str
    media_items: List[MediaItem] = Field(default_factory=list)

    @computed_field
    @property
    def has_media(self) -> bool:
        return len(self.media_items) > 0


class ProfileMediaResult(BaseModel):
    """Complete extraction result for an advanced profile query."""

    profile: ProfileInfo
    filter_options: ProfileFilterOptions
    tweets: List[ProfileTweetItem] = Field(default_factory=list)

    @computed_field
    @property
    def total_tweets(self) -> int:
        return len(self.tweets)

    @computed_field
    @property
    def total_media_items(self) -> int:
        return sum(len(t.media_items) for t in self.tweets)
