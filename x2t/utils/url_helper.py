"""URL parsing and validation utilities for X / Twitter links and profiles."""

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

# Matches profile URLs (e.g., https://x.com/username or https://twitter.com/username)
PROFILE_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|mobile\.|m\.)?(?:twitter\.com|x\.com)/(?:#!/)?(?P<user>[A-Za-z0-9_]{1,30})(?:/media|/with_replies)?/?(?:\?[^#\s]*)?$",
    re.IGNORECASE,
)

# Matches raw @username or standalone username handles
USERNAME_HANDLE_PATTERN = re.compile(r"^@?(?P<user>[A-Za-z0-9_]{1,30})$")

# Reserved words that are not valid user profile handles
RESERVED_USERNAMES = {
    "home", "explore", "notifications", "messages", "settings", "search",
    "tos", "privacy", "i", "account", "login", "signup", "intent", "hashtag",
    "help", "about", "status", "share", "download",
}


def extract_tweet_id(url_or_id: str) -> Optional[str]:
    """Extract numeric tweet ID from a URL or validate a raw numeric ID."""
    clean_input = url_or_id.strip()

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
        if user.lower() not in RESERVED_USERNAMES:
            return user
    return None


def extract_profile_username(url_or_handle: str) -> Optional[str]:
    """Extract Twitter username from a profile URL or @handle.

    Examples:
        >>> extract_profile_username("https://x.com/elonmusk")
        'elonmusk'
        >>> extract_profile_username("@NASA")
        'NASA'
        >>> extract_profile_username("https://twitter.com/SpaceX/media")
        'SpaceX'
        >>> extract_profile_username("https://x.com/elonmusk/status/123456")
        None
    """
    clean = url_or_handle.strip()

    # Exclude if it is a specific tweet status link
    if extract_tweet_id(clean):
        return None

    # Check profile URL pattern
    match = PROFILE_URL_PATTERN.match(clean)
    if match:
        user = match.group("user")
        if user.lower() not in RESERVED_USERNAMES:
            return user

    # Check @username or plain username
    match_handle = USERNAME_HANDLE_PATTERN.match(clean)
    if match_handle:
        user = match_handle.group("user")
        if user.lower() not in RESERVED_USERNAMES:
            return user

    return None


def is_profile_input(url_or_handle: str) -> bool:
    """True if input is a valid profile URL or username."""
    return extract_profile_username(url_or_handle) is not None


def normalize_tweet_url(url_or_id: str) -> str:
    """Returns canonical https://x.com/user/status/<tweet_id> URL."""
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
