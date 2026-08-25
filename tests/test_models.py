"""Unit tests for models."""

from x2t.models import MediaItem, MediaType, PostMediaResult


def test_models_counts():
    result = PostMediaResult(
        tweet_id="123456789",
        original_url="https://x.com/user/status/123456789",
        canonical_url="https://x.com/user/status/123456789",
        text="Test tweet with multiple media",
        items=[
            MediaItem(
                id="1",
                type=MediaType.VIDEO,
                url="https://video.twimg.com/vid1.mp4",
                width=1920,
                height=1080,
            ),
            MediaItem(
                id="2",
                type=MediaType.GIF,
                url="https://video.twimg.com/gif1.mp4",
                width=500,
                height=500,
                is_gif=True,
            ),
            MediaItem(
                id="3",
                type=MediaType.PHOTO,
                url="https://pbs.twimg.com/media/pic1.jpg",
                width=1200,
                height=800,
            ),
        ],
    )

    assert result.has_media is True
    assert result.media_count == 3
    assert result.video_count == 1
    assert result.gif_count == 1
    assert result.photo_count == 1
    assert result.items[0].resolution == "1920x1080"
