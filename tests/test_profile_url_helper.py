"""Unit tests for profile URL and username parsing."""

import pytest
from x2t.utils.url_helper import extract_profile_username, is_profile_input


@pytest.mark.parametrize(
    "input_text,expected_username",
    [
        ("@elonmusk", "elonmusk"),
        ("NASA", "NASA"),
        ("@SpaceX", "SpaceX"),
        ("https://x.com/elonmusk", "elonmusk"),
        ("https://twitter.com/NASA", "NASA"),
        ("https://mobile.twitter.com/SpaceX/media", "SpaceX"),
        ("http://x.com/user_123", "user_123"),
    ],
)
def test_extract_profile_username_valid(input_text, expected_username):
    assert extract_profile_username(input_text) == expected_username
    assert is_profile_input(input_text) is True


@pytest.mark.parametrize(
    "input_text",
    [
        ("https://x.com/elonmusk/status/1234567890"),
        ("https://twitter.com/NASA/status/9876543210/video/1"),
        ("https://x.com/home"),
        ("https://twitter.com/explore"),
        ("https://x.com/settings"),
        ("https://google.com"),
    ],
)
def test_extract_profile_username_invalid(input_text):
    assert extract_profile_username(input_text) is None
