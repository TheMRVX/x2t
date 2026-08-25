"""URL parsing and validation utilities for X / Twitter links."""

import re
from typing import Optional
from urllib.parse import urlparse

# Matches standard tweet status URLs from twitter.com, x.com, mobile.twitter.com, etc.
TWEET_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|mobile\.|m\.)?(?:twitter\.com|x\.com)/(?:#!/)?(?P<user>[A-Za-z0-9_]+)/status/(?P<id>\d+)",
    re.IGNORECASE,
)

# Matches direct numeric tweet IDs
NUMERIC_ID_PATTERN = re.compile(r"^\d{5,25}$")


def extract_tweet_id(url_or_id: str) -> Optional[str]:
    """Extract numeric tweet ID from a URL or validate a raw numeric ID.

    Examples:
        >>> extract_tweet_id("https://x.com/elonmusk/status/1825123456789012345")
        '1825123456789012345'
        >>> extract_tweet_id("https://twitter.com/i/status/1825123456789012345?s=20")
        '1825123456789012345'
        >>> extract_tweet_id("1825123456789012345")
        '1825123456789012345'
    """
    clean_input = url_or_id.strip()

    # Direct ID check
    if NUMERIC_ID_PATTERN.match(clean_input):
        return clean_input

    match = TWEET_URL_PATTERN.search(clean_input)
    if match:
        return match.group("id")

    return None


def extract_tweet_author(url: str) -> Optional[str]:
    """Extract username handle from a tweet URL if present."""
    match = TWEET_URL_PATTERN.search(url.strip())
    if match:
        user = match.group("user")
        if user.lower() not in ("i", "status"):
            return user
    return None


def normalize_tweet_url(url_or_id: str) -> str:
    """Returns canonical https://x.com/i/status/<tweet_id> URL.

    Raises:
        ValueError: If URL or ID is not a valid tweet identifier.
    """
    tweet_id = extract_tweet_id(url_or_id)
    if not tweet_id:
        raise ValueError(f"Invalid X/Twitter post URL or ID: {url_or_id}")

    author = extract_tweet_author(url_or_id)
    if author:
        return f"https://x.com/{author}/status/{tweet_id}"
    return f"https://x.com/i/status/{tweet_id}"


def is_valid_tweet_url(url_or_id: str) -> bool:
    """Check if the provided input is a valid tweet URL or ID."""
    return extract_tweet_id(url_or_id) is not None
