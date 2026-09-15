"""Unit tests for Twitter GraphQL backend and syndication tombstone handling."""

from unittest.mock import MagicMock, patch
import pytest
from x2t.core.extractor import XMediaExtractor
from x2t.core.graphql_backend import TwitterGraphQLBackend
from x2t.core.syndication_backend import SyndicationBackend
from x2t.exceptions import TweetNotFoundError
from x2t.models import MediaType


def test_graphql_backend_extract_success():
    backend = TwitterGraphQLBackend(auth_token="dummy_token", ct0="dummy_ct0")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "tweetResult": {
                "result": {
                    "__typename": "Tweet",
                    "core": {
                        "user_results": {
                            "result": {
                                "legacy": {
                                    "name": "Test User",
                                    "screen_name": "testuser",
                                }
                            }
                        }
                    },
                    "legacy": {
                        "full_text": "Hello world video https://t.co/abc",
                        "created_at": "Mon Sep 14 00:00:00 +0000 2026",
                        "extended_entities": {
                            "media": [
                                {
                                    "type": "video",
                                    "media_url_https": "https://pbs.twimg.com/thumb.jpg",
                                    "original_info": {"width": 1280, "height": 720},
                                    "video_info": {
                                        "duration_millis": 15000,
                                        "variants": [
                                            {
                                                "bitrate": 2176000,
                                                "content_type": "video/mp4",
                                                "url": "https://video.twimg.com/vid1.mp4",
                                            }
                                        ],
                                    },
                                }
                            ]
                        },
                    },
                }
            }
        }
    }

    with patch.object(backend.client, "get", return_value=mock_resp):
        res = backend.extract("https://x.com/testuser/status/1234567890")
        assert res.tweet_id == "1234567890"
        assert res.has_media is True
        assert res.author_username == "testuser"
        assert len(res.items) == 1
        assert res.items[0].type == MediaType.VIDEO
        assert res.items[0].url == "https://video.twimg.com/vid1.mp4"


def test_syndication_backend_rejects_tombstone():
    backend = SyndicationBackend()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"__typename": "TweetTombstone", "tombstone": {}}

    with patch.object(backend.client, "get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="tombstone"):
            backend.extract("https://x.com/testuser/status/1234567890")


def test_extractor_graphql_priority_with_auth():
    extractor = XMediaExtractor(auth_token="valid_token", ct0="valid_ct0")

    mock_graphql_result = MagicMock()
    mock_graphql_result.has_media = True
    mock_graphql_result.tweet_id = "1234567890"
    mock_graphql_result.model_copy.return_value = mock_graphql_result

    with patch.object(extractor.graphql_backend, "extract", return_value=mock_graphql_result) as mock_gql:
        with patch.object(extractor.fxtwitter_backend, "extract") as mock_fx:
            res = extractor.extract_info("https://x.com/testuser/status/1234567890")
            assert mock_gql.call_count == 1
            assert mock_fx.call_count == 0  # Should not fallback since GraphQL succeeded
            assert res.tweet_id == "1234567890"
