"""Unit tests for profile content filtering logic."""

import pytest
from x2t.core.profile_extractor import ProfileExtractor
from x2t.models import MediaItem, MediaType, ProfileFilterOptions, ProfileTweetItem


def create_sample_post(
    tweet_id: str,
    media_type: MediaType,
    is_retweet: bool = False,
    is_quote: bool = False,
    source_user: str = None,
) -> ProfileTweetItem:
    return ProfileTweetItem(
        tweet_id=tweet_id,
        canonical_url=f"https://x.com/testuser/status/{tweet_id}",
        text=f"Sample post {tweet_id}",
        is_retweet=is_retweet,
        is_quote=is_quote,
        source_user=source_user,
        author_username="testuser",
        author_name="Test User",
        media_items=[
            MediaItem(
                id="1",
                type=media_type,
                url="https://video.twimg.com/sample.mp4" if media_type == MediaType.VIDEO else "https://pbs.twimg.com/sample.jpg",
            )
        ],
    )


def test_default_filter_options():
    options = ProfileFilterOptions()
    assert options.include_videos is True
    assert options.include_photos is True
    assert options.include_gifs is True
    assert options.include_retweets is False
    assert options.include_sourced_media is False
    assert options.include_quotes is False
    assert options.limit == 10


def test_profile_filtering_rules():
    extractor = ProfileExtractor()
    sample_posts = [
        create_sample_post("1", MediaType.VIDEO),                                     # 1. Original Video (Pass)
        create_sample_post("2", MediaType.PHOTO, is_retweet=True),                    # 2. Retweet Photo (Filter if RT False)
        create_sample_post("3", MediaType.VIDEO, source_user="other_creator"),         # 3. From @other Video (Filter if Source False)
        create_sample_post("4", MediaType.GIF, is_quote=True),                        # 4. Quote GIF (Filter if Quote False)
        create_sample_post("5", MediaType.PHOTO),                                     # 5. Original Photo (Pass)
    ]

    # Test 1: Default Strict Mode (No RT, No Sourced, No Quotes)
    options_default = ProfileFilterOptions(limit=10)
    extractor._fetch_recent_posts_raw = lambda u, limit: list(sample_posts)
    result_default = extractor.fetch_profile_media_tweets("testuser", options_default)
    tweet_ids = [t.tweet_id for t in result_default.tweets]
    assert tweet_ids == ["1", "5"]

    # Test 2: Enable Retweets
    options_with_rt = ProfileFilterOptions(include_retweets=True, limit=10)
    result_rt = extractor.fetch_profile_media_tweets("testuser", options_with_rt)
    tweet_ids_rt = [t.tweet_id for t in result_rt.tweets]
    assert tweet_ids_rt == ["1", "2", "5"]

    # Test 3: Enable Sourced Media
    options_with_src = ProfileFilterOptions(include_sourced_media=True, limit=10)
    result_src = extractor.fetch_profile_media_tweets("testuser", options_with_src)
    tweet_ids_src = [t.tweet_id for t in result_src.tweets]
    assert tweet_ids_src == ["1", "3", "5"]

    # Test 4: Disable Photos (Only Videos)
    options_only_video = ProfileFilterOptions(include_photos=False, limit=10)
    result_video = extractor.fetch_profile_media_tweets("testuser", options_only_video)
    tweet_ids_video = [t.tweet_id for t in result_video.tweets]
    assert tweet_ids_video == ["1"]
