"""Unit tests for media sender and caption formatting."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from x2t.bot.services.media_sender import cleanup_temp_media, format_tweet_caption, send_post_media
from x2t.models import MediaItem, MediaType, PostMediaResult


def test_format_tweet_caption():
    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        text="Hello world <test>",
        author_name="John & Doe",
        author_username="johndoe",
        items=[],
    )
    caption = format_tweet_caption(result)
    assert "John &amp; Doe" in caption
    assert "@johndoe" in caption
    assert "Hello world &lt;test&gt;" in caption
    assert "@x2t_bot" in caption


def test_cleanup_temp_media(tmp_path):
    dummy_file = tmp_path / "temp_video.mp4"
    dummy_file.write_text("content")
    assert dummy_file.exists()

    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        items=[
            MediaItem(
                id="1",
                type=MediaType.VIDEO,
                url="https://video.twimg.com/1.mp4",
                local_path=str(dummy_file),
            )
        ],
    )

    cleanup_temp_media(result)
    assert not dummy_file.exists()


@pytest.mark.asyncio
async def test_send_post_media_single_video(tmp_path):
    dummy_file = tmp_path / "video.mp4"
    dummy_file.write_text("fake video data")

    bot_mock = MagicMock()
    bot_mock.send_video = AsyncMock(return_value=MagicMock())

    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        items=[
            MediaItem(
                id="1",
                type=MediaType.VIDEO,
                url="https://video.twimg.com/1.mp4",
                width=1280,
                height=720,
                duration_seconds=10.0,
                local_path=str(dummy_file),
            )
        ],
    )

    msgs = await send_post_media(bot=bot_mock, chat_id=12345, result=result)
    assert len(msgs) == 1
    bot_mock.send_video.assert_called_once()
    assert not dummy_file.exists()  # Cleaned up automatically
