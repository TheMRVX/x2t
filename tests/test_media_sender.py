"""Unit tests for media sender and caption formatting."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from x2t.bot.config import bot_config
from x2t.bot.services.media_sender import cleanup_temp_media, format_tweet_caption, send_post_media
from x2t.models import MediaItem, MediaType, PostMediaResult


def test_format_tweet_caption_standard():
    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        text="Hello world <test>",
        author_name="John & Doe",
        author_username="johndoe",
        items=[],
    )
    caption = format_tweet_caption(result, clean_caption=False)
    assert "John &amp; Doe" in caption
    assert "@johndoe" in caption
    assert "Hello world &lt;test&gt;" in caption
    assert "@x2t_bot" in caption


def test_format_tweet_caption_clean_mode():
    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        text="Wanna fuck :3",
        author_name="Lukey",
        author_username="Twinky_lukey",
        items=[],
    )
    caption = format_tweet_caption(result, clean_caption=True)
    # Only the raw post text, no author, no handle, no bot attribution
    assert caption == "Wanna fuck :3"
    assert "Lukey" not in caption
    assert "@Twinky_lukey" not in caption
    assert "@x2t_bot" not in caption


def test_format_tweet_caption_clean_mode_empty_text():
    result = PostMediaResult(
        tweet_id="123",
        original_url="https://x.com/test/status/123",
        canonical_url="https://x.com/test/status/123",
        text="",
        author_name="Lukey",
        author_username="Twinky_lukey",
        items=[],
    )
    caption = format_tweet_caption(result, clean_caption=True)
    assert caption is None


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
        text="Sample post text",
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

    # 1. Clean caption mode test
    bot_config.clean_caption = True
    msgs = await send_post_media(bot=bot_mock, chat_id=12345, result=result)
    assert len(msgs) == 1
    bot_mock.send_video.assert_called_once()
    _, kwargs = bot_mock.send_video.call_args
    assert kwargs.get("caption") == "Sample post text"
    assert kwargs.get("reply_markup") is None  # No external X link button
    assert not dummy_file.exists()  # Cleaned up automatically
