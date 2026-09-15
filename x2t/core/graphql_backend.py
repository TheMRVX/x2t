"""Direct Twitter / X GraphQL API backend supporting authenticated sessions and guest fallback."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from x2t.config import config
from x2t.exceptions import (
    AgeRestrictedError,
    PrivateTweetError,
    TweetNotFoundError,
)
from x2t.models import MediaItem, MediaType, PostMediaResult
from x2t.utils.media_helper import get_orig_photo_url, select_best_video_variant
from x2t.utils.url_helper import extract_tweet_id, normalize_tweet_url

logger = logging.getLogger("x2t.graphql")

BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

TWEET_RESULT_BY_REST_ID_QUERY_IDS = [
    "Xl5pC_lBk_gcO2ItU39DQw",
    "VByj4b868s00P3kU7x428g",
    "xOhWgkuRnH5YPrA_7kWtqg",
    "2ICvd9TISxzyAU0vP-bNNA",
    "5GhibuA2A5424UR0J_S4jA",
]

TWEET_DETAIL_QUERY_IDS = [
    "U0HTv-bAWTBYylwEMT7x5A",
]


class TwitterGraphQLBackend:
    """Extracts media directly from Twitter/X GraphQL API using authenticated session or guest token."""

    def __init__(self, cookies_file: Optional[str] = None, auth_token: Optional[str] = None, ct0: Optional[str] = None):
        self.cookies_file = cookies_file or config.cookies_file
        self.client = httpx.Client(
            timeout=config.request_timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://x.com",
                "Referer": "https://x.com/",
            },
            follow_redirects=True,
        )
        self._auth_token: Optional[str] = auth_token
        self._ct0: Optional[str] = ct0
        self._guest_token: Optional[str] = None

        if not self._auth_token and self.cookies_file:
            self._load_cookies()

        if self._auth_token:
            self.set_twitter_auth_token(self._auth_token, self._ct0)

    def set_twitter_auth_token(self, auth_token: str, ct0: Optional[str] = None):
        """Dynamically configure Twitter auth_token and auto-resolve ct0 CSRF token if needed."""
        if not auth_token:
            return
        self._auth_token = auth_token.strip()
        self.client.cookies.set("auth_token", self._auth_token, domain=".x.com")

        if ct0:
            self._ct0 = ct0.strip()
            self.client.cookies.set("ct0", self._ct0, domain=".x.com")
        else:
            # Auto-acquire ct0 by pinging x.com/home
            try:
                self.client.get("https://x.com/home", follow_redirects=True)
                for cookie in self.client.cookies.jar:
                    if cookie.name == "ct0":
                        self._ct0 = cookie.value
                        break
                if self._ct0:
                    self.client.cookies.set("ct0", self._ct0, domain=".x.com")
                    logger.info("Successfully acquired ct0 CSRF token for GraphQL backend.")
            except Exception as e:
                logger.warning(f"Could not auto-fetch ct0 in GraphQL backend: {e}")

        logger.info("Updated Twitter auth_token in GraphQL backend.")

    def has_auth_token(self) -> bool:
        """True if Twitter auth token is configured."""
        return bool(self._auth_token)

    def _load_cookies(self):
        """Load cookies from cookies.txt if exists."""
        if self.cookies_file and Path(self.cookies_file).exists():
            try:
                import http.cookiejar
                jar = http.cookiejar.MozillaCookieJar(self.cookies_file)
                jar.load(ignore_discard=True, ignore_expires=True)
                for cookie in jar:
                    self.client.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
                    if cookie.name == "auth_token":
                        self._auth_token = cookie.value
                    elif cookie.name == "ct0":
                        self._ct0 = cookie.value
                logger.info(f"GraphQL backend loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.warning(f"GraphQL backend failed to load cookies from {self.cookies_file}: {e}")

    def _get_guest_token(self) -> str:
        """Activate and return guest token if no auth session is present."""
        if not self._guest_token:
            try:
                r = self.client.post(
                    "https://api.x.com/1.1/guest/activate.json",
                    headers={"Authorization": f"Bearer {BEARER}"},
                )
                if r.status_code == 200:
                    self._guest_token = r.json().get("guest_token")
            except Exception as e:
                logger.debug(f"Guest token activation failed: {e}")
        return self._guest_token or ""

    def _build_headers(self) -> Dict[str, str]:
        """Build GraphQL HTTP headers with CSRF and auth headers."""
        headers = {
            "Authorization": f"Bearer {BEARER}",
        }
        if self._auth_token:
            if self._ct0:
                headers["x-csrf-token"] = self._ct0
            headers["x-twitter-auth-type"] = "OAuth2Session"
            headers["x-twitter-active-user"] = "yes"
        else:
            gt = self._get_guest_token()
            if gt:
                headers["x-guest-token"] = gt
        return headers

    def extract(self, url_or_id: str) -> PostMediaResult:
        """Extract media directly from Twitter/X GraphQL API."""
        tweet_id = extract_tweet_id(url_or_id)
        if not tweet_id:
            raise ValueError(f"Could not extract tweet ID from '{url_or_id}'")

        canonical_url = normalize_tweet_url(url_or_id)

        features = {
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_enhance_cards_enabled": False,
        }

        headers = self._build_headers()

        # Method 1: Try TweetResultByRestId
        for query_id in TWEET_RESULT_BY_REST_ID_QUERY_IDS:
            try:
                url = f"https://x.com/i/api/graphql/{query_id}/TweetResultByRestId"
                params = {
                    "variables": json.dumps({
                        "tweetId": tweet_id,
                        "withCommunity": False,
                        "includePromotedContent": False,
                        "withVoice": False,
                    }),
                    "features": json.dumps(features),
                }
                resp = self.client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    tweet_result = data.get("data", {}).get("tweetResult", {}).get("result")
                    if tweet_result:
                        return self._parse_graphql_tweet(tweet_result, tweet_id, url_or_id, canonical_url)
            except (TweetNotFoundError, PrivateTweetError, AgeRestrictedError):
                raise
            except Exception as e:
                logger.debug(f"GraphQL TweetResultByRestId ({query_id}) error for {tweet_id}: {e}")

        # Method 2: Try TweetDetail fallback
        for query_id in TWEET_DETAIL_QUERY_IDS:
            try:
                url = f"https://x.com/i/api/graphql/{query_id}/TweetDetail"
                params = {
                    "variables": json.dumps({
                        "focalTweetId": tweet_id,
                        "with_rux_injections": False,
                        "includePromotedContent": True,
                        "withCommunity": True,
                        "withQuickPromoteEligibilityTweetFields": True,
                        "withBirdwatchNotes": True,
                        "withVoice": True,
                        "withV2Timeline": True,
                    }),
                    "features": json.dumps(features),
                    "fieldToggles": json.dumps({"withAuxiliaryUserLabels": False}),
                }
                resp = self.client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    tweet_result = self._extract_tweet_from_timeline(data, tweet_id)
                    if tweet_result:
                        return self._parse_graphql_tweet(tweet_result, tweet_id, url_or_id, canonical_url)
            except (TweetNotFoundError, PrivateTweetError, AgeRestrictedError):
                raise
            except Exception as e:
                logger.debug(f"GraphQL TweetDetail ({query_id}) error for {tweet_id}: {e}")

        raise RuntimeError(f"GraphQL backend could not resolve tweet {tweet_id}")

    def _extract_tweet_from_timeline(self, data: Dict[str, Any], tweet_id: str) -> Optional[Dict[str, Any]]:
        """Find focal tweet inside threaded conversation response."""
        instructions = (
            data.get("data", {})
            .get("threaded_conversation_with_injections_v2", {})
            .get("instructions", [])
        )
        for instr in instructions:
            entries = instr.get("entries", [])
            for entry in entries:
                entry_id = entry.get("entryId", "")
                if f"tweet-{tweet_id}" in entry_id:
                    item_content = entry.get("content", {}).get("itemContent", {})
                    return item_content.get("tweet_results", {}).get("result")
        return None

    def _parse_graphql_tweet(
        self, tweet_result: Dict[str, Any], tweet_id: str, original_url: str, canonical_url: str
    ) -> PostMediaResult:
        """Parse raw GraphQL tweet JSON into structured PostMediaResult."""
        typename = tweet_result.get("__typename")

        # Handle wrapped or tombstone tweets
        if typename == "TweetWithVisibilityResults":
            tweet_result = tweet_result.get("tweet", {})
            typename = tweet_result.get("__typename")

        if typename == "TweetTombstone" or "tombstone" in tweet_result:
            tombstone_text = (
                tweet_result.get("tombstone", {})
                .get("text", {})
                .get("text", "")
                .lower()
            )
            if "not found" in tombstone_text or "deleted" in tombstone_text:
                raise TweetNotFoundError(f"Tweet {tweet_id} was deleted or not found.", tweet_id=tweet_id)
            if "protected" in tombstone_text or "private" in tombstone_text:
                raise PrivateTweetError(f"Tweet {tweet_id} belongs to a protected account.")
            if "age" in tombstone_text or "sensitive" in tombstone_text:
                raise AgeRestrictedError(f"Tweet {tweet_id} is age-restricted.")
            raise RuntimeError(f"Tweet {tweet_id} is unavailable: {tombstone_text}")

        legacy = tweet_result.get("legacy", {})
        if not legacy:
            raise RuntimeError(f"Tweet {tweet_id} missing legacy payload in GraphQL response")

        # Author details
        user_result = (
            tweet_result.get("core", {})
            .get("user_results", {})
            .get("result", {})
        )
        user_legacy = user_result.get("legacy", {})
        author_name = user_legacy.get("name")
        author_username = user_legacy.get("screen_name")

        # Text content (support longform NoteTweet)
        note_tweet = (
            tweet_result.get("note_tweet", {})
            .get("note_tweet_results", {})
            .get("result", {})
            .get("text")
        )
        text = note_tweet or legacy.get("full_text") or legacy.get("text")
        created_at = legacy.get("created_at")

        # Media items
        extended_entities = legacy.get("extended_entities", {})
        media_list = extended_entities.get("media") or legacy.get("entities", {}).get("media", [])

        items: List[MediaItem] = []
        for idx, m in enumerate(media_list, start=1):
            m_type = m.get("type", "").lower()
            is_gif = m_type in ("animated_gif", "gif")
            is_video = m_type in ("video", "animated_gif", "gif")

            if is_video:
                video_info = m.get("video_info", {})
                variants = video_info.get("variants", [])
                duration_ms = video_info.get("duration_millis")
                duration_seconds = (duration_ms / 1000.0) if duration_ms else None

                best_variant = select_best_video_variant(variants, duration_seconds=duration_seconds)
                best_url = best_variant.get("url") if best_variant else None
                best_bitrate = best_variant.get("bitrate") if best_variant else None

                original_info = m.get("original_info", {})
                width = original_info.get("width")
                height = original_info.get("height")

                if best_url:
                    items.append(
                        MediaItem(
                            id=str(idx),
                            type=MediaType.GIF if is_gif else MediaType.VIDEO,
                            url=best_url,
                            width=width,
                            height=height,
                            bitrate=best_bitrate,
                            duration_seconds=duration_seconds,
                            thumbnail_url=m.get("media_url_https"),
                            is_gif=is_gif,
                        )
                    )
            elif m_type == "photo":
                photo_url = m.get("media_url_https") or m.get("url")
                if photo_url:
                    orig_url = get_orig_photo_url(photo_url)
                    original_info = m.get("original_info", {})
                    items.append(
                        MediaItem(
                            id=str(idx),
                            type=MediaType.PHOTO,
                            url=orig_url,
                            width=original_info.get("width"),
                            height=original_info.get("height"),
                            thumbnail_url=photo_url,
                            is_gif=False,
                        )
                    )

        return PostMediaResult(
            tweet_id=tweet_id,
            original_url=original_url,
            canonical_url=canonical_url,
            text=text,
            author_name=author_name,
            author_username=author_username,
            items=items,
            created_at=created_at,
        )
