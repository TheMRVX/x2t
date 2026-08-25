"""Unit tests for extractor TTL caching and token health check."""

import time
from unittest.mock import MagicMock, patch
import pytest
from x2t.core.extractor import XMediaExtractor
from x2t.core.profile_extractor import ProfileExtractor
from x2t.models import MediaItem, MediaType, PostMediaResult


def test_extractor_ttl_caching():
    """Verify that XMediaExtractor uses in-memory TTL caching for duplicate requests."""
    extractor = XMediaExtractor(cache_ttl_seconds=1.0)
    tweet_id = "1825123456789012345"
    url = f"https://x.com/user/status/{tweet_id}"

    sample_result = PostMediaResult(
        tweet_id=tweet_id,
        original_url=url,
        canonical_url=url,
        text="Cached Tweet Test",
        items=[
            MediaItem(
                id="1",
                type=MediaType.VIDEO,
                url="https://video.twimg.com/sample.mp4",
            )
        ],
    )

    with patch.object(extractor.fxtwitter_backend, "extract", return_value=sample_result) as mock_extract:
        # First call: Cache miss -> calls backend
        r1 = extractor.extract_info(url)
        assert r1.tweet_id == tweet_id
        assert mock_extract.call_count == 1

        # Second call: Cache hit -> does NOT call backend
        r2 = extractor.extract_info(url)
        assert r2.tweet_id == tweet_id
        assert mock_extract.call_count == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Third call: Cache expired -> calls backend again
        r3 = extractor.extract_info(url)
        assert r3.tweet_id == tweet_id
        assert mock_extract.call_count == 2


def test_token_health_check_no_token():
    """Verify token health check returns False when no token is set."""
    pe = ProfileExtractor()
    pe._auth_token = None
    is_valid, msg = pe.check_auth_token_health()
    assert is_valid is False
    assert "تنظیم نشده" in msg


def test_token_health_check_valid():
    """Verify token health check returns True when Twitter API returns 200."""
    pe = ProfileExtractor()
    pe._auth_token = "valid_token"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}

    with patch.object(pe.client, "get", return_value=mock_resp):
        is_valid, msg = pe.check_auth_token_health()
        assert is_valid is True
        assert "معتبر و فعال" in msg


def test_token_health_check_expired():
    """Verify token health check returns False when Twitter API returns 401."""
    pe = ProfileExtractor()
    pe._auth_token = "expired_token"

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.headers = {}

    with patch.object(pe.client, "get", return_value=mock_resp):
        is_valid, msg = pe.check_auth_token_health()
        assert is_valid is False
        assert "منقضی" in msg
