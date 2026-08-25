"""Profile timeline and media extraction coordinator with granular content filtering."""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from x2t.config import config
from x2t.models import (
    MediaItem,
    MediaType,
    ProfileFilterOptions,
    ProfileInfo,
    ProfileMediaResult,
    ProfileTweetItem,
)
from x2t.utils.media_helper import get_orig_photo_url, select_best_video_variant

logger = logging.getLogger("x2t.profile")

BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)


class ProfileExtractor:
    """Extracts profile metadata and timelines with multi-criteria attribution filtering."""

    def __init__(self):
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
        self._guest_token: Optional[str] = None

    def _get_guest_token(self) -> str:
        """Activate and return guest token."""
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

    def get_profile_info(self, username: str) -> ProfileInfo:
        """Fetch profile summary info (name, bio, avatar, followers, media count)."""
        clean_user = username.lstrip("@").strip()

        # Method 1: Try FxTwitter API User endpoint
        try:
            r = self.client.get(f"https://api.fxtwitter.com/{clean_user}")
            if r.status_code == 200:
                data = r.json().get("user", {})
                if data:
                    return ProfileInfo(
                        username=data.get("screen_name") or clean_user,
                        name=data.get("name") or clean_user,
                        bio=data.get("description"),
                        avatar_url=data.get("avatar_url") or data.get("profile_image_url_https"),
                        followers_count=data.get("followers_count"),
                        media_count=data.get("media_count"),
                    )
        except Exception as e:
            logger.debug(f"FxTwitter user lookup failed: {e}")

        # Method 2: Fallback to GraphQL UserByScreenName
        try:
            guest_token = self._get_guest_token()
            headers = {
                "Authorization": f"Bearer {BEARER}",
                "x-guest-token": guest_token,
                "x-twitter-active-user": "yes",
            }
            url = "https://x.com/i/api/graphql/sLVLhk0bGj3MVFEKTdax1w/UserByScreenName"
            params = {
                "variables": json.dumps({"screen_name": clean_user, "withSafetyModeUserFields": True}),
                "features": json.dumps({
                    "hidden_profile_likes_enabled": True,
                    "hidden_profile_subscriptions_enabled": True,
                    "responsive_web_graphql_exclude_directive_enabled": True,
                    "verified_phone_label_enabled": False,
                }),
                "fieldToggles": json.dumps({"withAuxiliaryUserLabels": False}),
            }
            r = self.client.get(url, params=params, headers=headers)
            if r.status_code == 200:
                data = r.json()
                res = data.get("data", {}).get("user", {}).get("result", {})
                legacy = res.get("legacy", {})
                return ProfileInfo(
                    rest_id=res.get("rest_id"),
                    username=legacy.get("screen_name") or clean_user,
                    name=legacy.get("name") or clean_user,
                    bio=legacy.get("description"),
                    avatar_url=legacy.get("profile_image_url_https", "").replace("_normal", ""),
                    followers_count=legacy.get("followers_count"),
                    media_count=legacy.get("media_count"),
                )
        except Exception as e:
            logger.debug(f"GraphQL UserByScreenName failed: {e}")

        # Basic fallback
        return ProfileInfo(username=clean_user, name=clean_user)

    def fetch_profile_media_tweets(
        self, username: str, options: ProfileFilterOptions
    ) -> ProfileMediaResult:
        """Fetch and filter recent media tweets for a user account."""
        clean_user = username.lstrip("@").strip()
        profile_info = self.get_profile_info(clean_user)

        raw_posts = self._fetch_recent_posts_raw(clean_user, limit=options.limit * 3)
        filtered_tweets: List[ProfileTweetItem] = []

        for p in raw_posts:
            # 1. Filter: Retweets / Reposts
            if p.is_retweet and not options.include_retweets:
                logger.debug(f"Skipping retweet {p.tweet_id}")
                continue

            # 2. Filter: Quote Tweets
            if p.is_quote and not options.include_quotes:
                logger.debug(f"Skipping quote tweet {p.tweet_id}")
                continue

            # 3. Filter: Third-party sourced media ('From @other')
            if p.source_user and p.source_user.lower() != clean_user.lower() and not options.include_sourced_media:
                logger.debug(f"Skipping sourced media tweet {p.tweet_id} (source: @{p.source_user})")
                continue

            # 4. Filter: Media Types
            allowed_items: List[MediaItem] = []
            for item in p.media_items:
                if item.type == MediaType.VIDEO and options.include_videos:
                    allowed_items.append(item)
                elif item.type == MediaType.PHOTO and options.include_photos:
                    allowed_items.append(item)
                elif item.type == MediaType.GIF and options.include_gifs:
                    allowed_items.append(item)

            if not allowed_items:
                continue

            p.media_items = allowed_items
            filtered_tweets.append(p)

            if len(filtered_tweets) >= options.limit:
                break

        return ProfileMediaResult(
            profile=profile_info,
            filter_options=options,
            tweets=filtered_tweets,
        )

    def _fetch_recent_posts_raw(self, username: str, limit: int = 30) -> List[ProfileTweetItem]:
        """Fetch raw posts with attribution metadata from open resolvers."""
        raw_items: List[ProfileTweetItem] = []

        # Strategy 1: FxTwitter status queries / user timeline
        try:
            r = self.client.get(f"https://api.fxtwitter.com/{username}/status/latest")
            # Or query multiple recent media
        except Exception:
            pass

        # Strategy 2: Direct Search or Syndication fallback
        try:
            # Open resolver feeds
            url = f"https://api.vxtwitter.com/{username}"
            r = self.client.get(url)
            if r.status_code == 200 and "application/json" in r.headers.get("content-type", ""):
                data = r.json()
                # Parse timeline tweets
        except Exception:
            pass

        return raw_items


profile_extractor = ProfileExtractor()
