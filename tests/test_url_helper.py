"""Unit tests for URL helper functions."""

import pytest
from x2t.utils.url_helper import (
    extract_tweet_author,
    extract_tweet_id,
    is_valid_tweet_url,
    normalize_tweet_url,
)


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://twitter.com/jack/status/20", "20"),
        ("https://x.com/elonmusk/status/1825123456789012345", "1825123456789012345"),
        ("https://mobile.twitter.com/user/status/123456789?s=20", "123456789"),
        ("https://m.twitter.com/user/status/9876543210/video/1", "9876543210"),
        ("https://x.com/i/status/112233445566", "112233445566"),
        ("1825123456789012345", "1825123456789012345"),
    ],
)
def test_extract_tweet_id(url, expected_id):
    assert extract_tweet_id(url) == expected_id


def test_invalid_urls():
    assert extract_tweet_id("https://google.com") is None
    assert extract_tweet_id("https://x.com/home") is None
    assert extract_tweet_id("not_a_url") is None
    assert not is_valid_tweet_url("random_string")


def test_extract_tweet_author():
    assert extract_tweet_author("https://x.com/elonmusk/status/123456") == "elonmusk"
    assert extract_tweet_author("https://twitter.com/jack/status/20") == "jack"
    assert extract_tweet_author("https://x.com/i/status/123456") is None


def test_normalize_tweet_url():
    assert (
        normalize_tweet_url("https://twitter.com/jack/status/20?s=20")
        == "https://x.com/jack/status/20"
    )
    assert (
        normalize_tweet_url("1825123456789012345")
        == "https://x.com/i/status/1825123456789012345"
    )
