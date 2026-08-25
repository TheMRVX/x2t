"""Profile timeline and media extraction coordinator with granular content filtering."""

import json
import logging
from pathlib import Path
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

USER_TWEETS_QUERY_ID = "V7H0Ap3_Hh2FyS75OCDO3Q"


class ProfileExtractor:
    """Extracts profile metadata and timelines with multi-criteria attribution filtering."""

    def __init__(self, cookies_file: Optional[str] = None):
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
        self._guest_token: Optional[str] = None
        self._load_cookies()

    def set_twitter_auth_token(self, auth_token: str, ct0: Optional[str] = None):
        """Dynamically set Twitter auth token and ct0."""
        self.client.cookies.set("auth_token", auth_token.strip(), domain=".x.com")
        self.client.cookies.set("auth_token", auth_token.strip(), domain=".twitter.com")
        if ct0:
            self.client.cookies.set("ct0", ct0.strip(), domain=".x.com")
            self.client.cookies.set("ct0", ct0.strip(), domain=".twitter.com")
        logger.info("Updated Twitter auth_token in ProfileExtractor client.")

    def has_auth_cookies(self) -> bool:
        """True if auth_token is present in cookies."""
        return bool(self.client.cookies.get("auth_token"))

    def _load_cookies(self):
        """Load cookies from cookies.txt or environment if exists."""
        if self.cookies_file and Path(self.cookies_file).exists():
            try:
                import http.cookiejar
                jar = http.cookiejar.MozillaCookieJar(self.cookies_file)
                jar.load(ignore_discard=True, ignore_expires=True)
                for cookie in jar:
                    self.client.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
                logger.info(f"Loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.warning(f"Failed to load cookies from {self.cookies_file}: {e}")

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
        """Fetch profile summary info (name, bio, avatar, followers, media count, rest_id)."""
        clean_user = username.lstrip("@").strip()

        # Method 1: Try FxTwitter API User endpoint
        try:
            r = self.client.get(f"https://api.fxtwitter.com/{clean_user}")
            if r.status_code == 200:
                data = r.json().get("user", {})
                if data:
                    return ProfileInfo(
                        rest_id=data.get("id"),
                        username=data.get("screen_name") or clean_user,
                        name=data.get("name") or clean_user,
                        bio=data.get("description"),
                        avatar_url=data.get("avatar_url") or data.get("profile_image_url_https"),
                        followers_count=data.get("followers"),
                        media_count=data.get("media_count"),
                    )
        except Exception as e:
            logger.debug(f"FxTwitter user lookup failed: {e}")

        # Method 2: Fallback to GraphQL UserByScreenName
        try:
            headers = self._build_graphql_headers()
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

    def _build_graphql_headers(self) -> Dict[str, str]:
        """Build request headers depending on whether auth cookies exist."""
        headers = {
            "Authorization": f"Bearer {BEARER}",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
        }

        auth_token = self.client.cookies.get("auth_token")
        ct0 = self.client.cookies.get("ct0")

        if auth_token:
            headers["x-twitter-auth-type"] = "OAuth2Session"
            if ct0:
                headers["x-csrf-token"] = ct0
        else:
            headers["x-guest-token"] = self._get_guest_token()

        return headers

    def fetch_profile_media_tweets(
        self, username: str, options: ProfileFilterOptions
    ) -> ProfileMediaResult:
        """Fetch and filter recent media tweets for a user account."""
        clean_user = username.lstrip("@").strip()
        profile_info = self.get_profile_info(clean_user)

        raw_posts = self._fetch_recent_posts_raw(profile_info, limit=options.limit * 3)
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

    def _fetch_recent_posts_raw(self, profile: ProfileInfo, limit: int = 30) -> List[ProfileTweetItem]:
        """Fetch raw posts with attribution metadata from Twitter GraphQL."""
        raw_items: List[ProfileTweetItem] = []
        user_id = profile.rest_id

        if not user_id:
            logger.warning(f"No rest_id for user {profile.username}")
            return raw_items

        headers = self._build_graphql_headers()

        features = {
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "tweetypie_unmention_optimization_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_media_download_video_enabled": False,
            "responsive_web_enhance_cards_enabled": False,
        }

        url = f"https://x.com/i/api/graphql/{USER_TWEETS_QUERY_ID}/UserTweets"
        params = {
            "variables": json.dumps({
                "userId": str(user_id),
                "count": max(20, limit),
                "includePromotedContent": False,
                "withClientEventToken": False,
                "withBirdwatchNotes": False,
                "withVoice": False,
                "withV2Timeline": True,
            }),
            "features": json.dumps(features),
        }

        try:
            r = self.client.get(url, params=params, headers=headers)
            if r.status_code == 200:
                data = r.json()
                instructions = (
                    data.get("data", {})
                    .get("user", {})
                    .get("result", {})
                    .get("timeline_v2", {})
                    .get("timeline", {})
                    .get("instructions", [])
                )
                for inst in instructions:
                    entries = inst.get("entries", [])
                    for e in entries:
                        item_content = e.get("content", {}).get("itemContent", {})
                        tweet_results = item_content.get("tweet_results", {})
                        result = tweet_results.get("result", {})
                        if not result:
                            continue

                        typename = result.get("__typename")
                        if typename == "TweetWithVisibilityResults":
                            result = result.get("tweet", {})

                        legacy = result.get("legacy", {})
                        if not legacy:
                            continue

                        tweet_id = result.get("rest_id") or legacy.get("id_str")
                        if not tweet_id:
                            continue

                        # Extract text and attribution flags
                        text = legacy.get("full_text", "")
                        is_rt = "retweeted_status_result" in legacy or text.startswith("RT @")
                        is_quote = legacy.get("is_quote_status", False)

                        # Extract media elements
                        extended_entities = legacy.get("extended_entities", {})
                        media_list = extended_entities.get("media", [])
                        if not media_list:
                            media_list = legacy.get("entities", {}).get("media", [])

                        if not media_list:
                            continue

                        # Check sourced attribution (From @other_user)
                        source_user = None
                        first_media = media_list[0] if media_list else {}
                        add_info = first_media.get("additional_media_info", {})
                        if add_info and "source_user" in add_info:
                            source_user = add_info.get("source_user", {}).get("legacy", {}).get("screen_name")
                        elif first_media.get("source_user_id_str") and first_media.get("source_user_id_str") != str(user_id):
                            source_user = "third_party"

                        items: List[MediaItem] = []
                        for idx, m in enumerate(media_list, start=1):
                            m_type_str = m.get("type", "").lower()
                            is_video = m_type_str in ("video", "animated_gif")
                            is_gif = m_type_str == "animated_gif"

                            if is_video:
                                video_info = m.get("video_info", {})
                                variants = video_info.get("variants", [])
                                best_v = select_best_video_variant(variants, duration_seconds=video_info.get("duration_millis", 0) / 1000.0)
                                if best_v and "url" in best_v:
                                    items.append(
                                        MediaItem(
                                            id=str(idx),
                                            type=MediaType.GIF if is_gif else MediaType.VIDEO,
                                            url=best_v["url"],
                                            width=m.get("original_info", {}).get("width"),
                                            height=m.get("original_info", {}).get("height"),
                                            bitrate=best_v.get("bitrate"),
                                            duration_seconds=video_info.get("duration_millis", 0) / 1000.0 if video_info.get("duration_millis") else None,
                                            thumbnail_url=m.get("media_url_https"),
                                            is_gif=is_gif,
                                        )
                                    )
                            else:  # Photo
                                photo_url = m.get("media_url_https")
                                if photo_url:
                                    orig_url = get_orig_photo_url(photo_url)
                                    items.append(
                                        MediaItem(
                                            id=str(idx),
                                            type=MediaType.PHOTO,
                                            url=orig_url,
                                            width=m.get("original_info", {}).get("width"),
                                            height=m.get("original_info", {}).get("height"),
                                            thumbnail_url=photo_url,
                                            is_gif=False,
                                        )
                                    )

                        if items:
                            raw_items.append(
                                ProfileTweetItem(
                                    tweet_id=tweet_id,
                                    canonical_url=f"https://x.com/{profile.username}/status/{tweet_id}",
                                    text=text,
                                    created_at=legacy.get("created_at"),
                                    is_retweet=is_rt,
                                    is_quote=is_quote,
                                    source_user=source_user,
                                    author_username=profile.username,
                                    author_name=profile.name,
                                    media_items=items,
                                )
                            )

        except Exception as e:
            logger.error(f"Failed to fetch timeline for {profile.username}: {e}", exc_info=True)

        return raw_items


profile_extractor = ProfileExtractor()
