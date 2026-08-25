"""Integration tests for x2t extractor and downloader."""

import pytest
import x2t
from x2t.models import MediaType


def test_extract_video_tweet():
    """Test extracting a standard video post."""
    result = x2t.extract_media("https://twitter.com/BrooklynNets/status/1349794411333394432")
    assert result.tweet_id == "1349794411333394432"
    assert result.has_media is True
    assert result.video_count >= 1
    assert result.author_username == "BrooklynNets"
    first = result.items[0]
    assert first.type == MediaType.VIDEO
    assert first.url.startswith("https://video.twimg.com/")
    assert first.width == 1280
    assert first.height == 720


def test_extract_multi_media_tweet():
    """Test extracting a post with 4 media items."""
    result = x2t.extract_media("https://twitter.com/UltimaShadowX/status/1577719286659006464")
    assert result.tweet_id == "1577719286659006464"
    assert result.media_count == 4
    assert result.gif_count == 4
    for item in result.items:
        assert item.type == MediaType.GIF
        assert item.is_gif is True
        assert item.url.startswith("https://video.twimg.com/")


def test_download_media(tmp_path):
    """Test downloading media to a temporary directory."""
    result = x2t.download_media(
        "https://twitter.com/UltimaShadowX/status/1577719286659006464",
        output_dir=tmp_path,
    )
    assert result.media_count == 4
    for item in result.items:
        assert item.is_downloaded is True
        assert item.local_path is not None
        assert item.size_bytes > 1000  # valid file size (>1KB)
