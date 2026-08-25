"""Unit tests for media helper functions."""

from x2t.models import MediaType
from x2t.utils.media_helper import (
    generate_filename,
    get_orig_photo_url,
    select_best_video_variant,
)


def test_get_orig_photo_url():
    url = "https://pbs.twimg.com/media/GQ_Abc123.jpg"
    orig = get_orig_photo_url(url)
    assert "format=jpg" in orig
    assert "name=orig" in orig


def test_select_best_video_variant():
    variants = [
        {"content_type": "application/x-mpegURL", "url": "https://video.twimg.com/m3u8"},
        {"content_type": "video/mp4", "bitrate": 256000, "url": "https://video.twimg.com/256.mp4"},
        {"content_type": "video/mp4", "bitrate": 2176000, "url": "https://video.twimg.com/1080.mp4"},
        {"content_type": "video/mp4", "bitrate": 832000, "url": "https://video.twimg.com/720.mp4"},
    ]
    best = select_best_video_variant(variants)
    assert best is not None
    assert best["url"] == "https://video.twimg.com/1080.mp4"
    assert best["bitrate"] == 2176000


def test_generate_filename():
    assert generate_filename("12345", 1, MediaType.VIDEO) == "tweet_12345_video_1.mp4"
    assert generate_filename("12345", 2, MediaType.GIF) == "tweet_12345_gif_2.mp4"
    assert generate_filename("12345", 3, MediaType.PHOTO, "png") == "tweet_12345_photo_3.png"
