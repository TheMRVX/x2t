"""FxTwitter / VxTwitter public resolver backend for sensitive and standard tweets."""

import logging
from typing import Any, Dict, List, Optional
import httpx

from x2t.config import config
from x2t.models import MediaItem, MediaType, PostMediaResult
from x2t.utils.media_helper import get_orig_photo_url, select_best_video_variant
from x2t.utils.url_helper import extract_tweet_author, extract_tweet_id, normalize_tweet_url

logger = logging.getLogger("x2t.fxtwitter")


class FxTwitterBackend:
    """Extracts media from Twitter/X using high-reliability open resolvers (fxtwitter / vxtwitter)."""

    def __init__(self):
        self.client = httpx.Client(
            timeout=config.request_timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
            follow_redirects=True,
        )

    def extract(self, url_or_id: str) -> PostMediaResult:
        """Extract media using fxtwitter API with fallback to vxtwitter."""
        tweet_id = extract_tweet_id(url_or_id)
        if not tweet_id:
            raise ValueError(f"Could not extract tweet ID from '{url_or_id}'")

        canonical_url = normalize_tweet_url(url_or_id)
        author = extract_tweet_author(url_or_id) or "i"

        # 1. Try fxtwitter API
        try:
            endpoints = [
                f"https://api.fxtwitter.com/status/{tweet_id}",
                f"https://api.fxtwitter.com/{author}/status/{tweet_id}",
            ]
            for ep in endpoints:
                resp = self.client.get(ep)
                if resp.status_code == 200:
                    data = resp.json()
                    tweet = data.get("tweet")
                    if tweet:
                        return self._parse_fxtwitter_data(tweet, tweet_id, url_or_id, canonical_url)
        except Exception as e:
            logger.debug(f"FxTwitter request failed: {e}")

        # 2. Try vxtwitter API fallback
        try:
            vx_endpoints = [
                f"https://api.vxtwitter.com/Twitter/status/{tweet_id}",
                f"https://api.vxtwitter.com/{author}/status/{tweet_id}",
            ]
            for ep in vx_endpoints:
                resp = self.client.get(ep)
                if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
                    data = resp.json()
                    return self._parse_vxtwitter_data(data, tweet_id, url_or_id, canonical_url)
        except Exception as e:
            logger.debug(f"VxTwitter request failed: {e}")

        raise RuntimeError(f"FxTwitter/VxTwitter backend could not find media for tweet {tweet_id}")

    def _parse_fxtwitter_data(
        self, tweet: Dict[str, Any], tweet_id: str, original_url: str, canonical_url: str
    ) -> PostMediaResult:
        text = tweet.get("text")
        author_dict = tweet.get("author", {})
        author_name = author_dict.get("name")
        author_username = author_dict.get("screen_name")
        created_at = tweet.get("created_at")

        media_container = tweet.get("media", {})
        all_media = media_container.get("all", [])
        if not all_media:
            # Check separate photos/videos/gifs arrays
            all_media = (
                media_container.get("videos", [])
                + media_container.get("gifs", [])
                + media_container.get("photos", [])
            )

        items: List[MediaItem] = []
        for idx, m in enumerate(all_media, start=1):
            m_type_str = m.get("type", "").lower()
            is_gif = m_type_str in ("gif", "animated_gif")
            is_video = m_type_str in ("video", "gif", "animated_gif")

            if is_video:
                # Find best video variant from variants or formats
                best_url = m.get("url")
                best_bitrate = None

                variants = m.get("variants") or []
                duration = m.get("duration")
                width = m.get("width")
                height = m.get("height")
                if variants:
                    best_v = select_best_video_variant(variants, duration_seconds=duration)
                    if best_v and "url" in best_v:
                        best_url = best_v["url"]
                        best_bitrate = best_v.get("bitrate")
                        # Extract dimensions from URL if present (e.g. 720x1280)
                        import re
                        dim_match = re.search(r"/(\d+)x(\d+)/", best_url)
                        if dim_match:
                            width = int(dim_match.group(1))
                            height = int(dim_match.group(2))

                items.append(
                    MediaItem(
                        id=str(idx),
                        type=MediaType.GIF if is_gif else MediaType.VIDEO,
                        url=best_url,
                        width=width,
                        height=height,
                        bitrate=best_bitrate,
                        duration_seconds=duration,
                        thumbnail_url=m.get("thumbnail_url"),
                        is_gif=is_gif,
                    )
                )
            else:  # Photo
                photo_url = m.get("url")
                if photo_url:
                    orig_url = get_orig_photo_url(photo_url)
                    items.append(
                        MediaItem(
                            id=str(idx),
                            type=MediaType.PHOTO,
                            url=orig_url,
                            width=m.get("width"),
                            height=m.get("height"),
                            thumbnail_url=m.get("thumbnail_url") or photo_url,
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

    def _parse_vxtwitter_data(
        self, data: Dict[str, Any], tweet_id: str, original_url: str, canonical_url: str
    ) -> PostMediaResult:
        text = data.get("text")
        author_name = data.get("user_name")
        author_username = data.get("user_screen_name")
        created_at = data.get("date")

        items: List[MediaItem] = []
        media_extended = data.get("media_extended", [])

        for idx, m in enumerate(media_extended, start=1):
            m_type = m.get("type", "").lower()
            is_gif = m_type in ("gif", "animated_gif")
            is_video = m_type in ("video", "gif", "animated_gif")
            size = m.get("size", {})

            if is_video:
                items.append(
                    MediaItem(
                        id=str(idx),
                        type=MediaType.GIF if is_gif else MediaType.VIDEO,
                        url=m.get("url"),
                        width=size.get("width") if size else None,
                        height=size.get("height") if size else None,
                        duration_seconds=m.get("duration_millis", 0) / 1000.0 if m.get("duration_millis") else None,
                        thumbnail_url=m.get("thumbnail_url"),
                        is_gif=is_gif,
                    )
                )
            else:
                photo_url = m.get("url")
                if photo_url:
                    orig_url = get_orig_photo_url(photo_url)
                    items.append(
                        MediaItem(
                            id=str(idx),
                            type=MediaType.PHOTO,
                            url=orig_url,
                            width=size.get("width") if size else None,
                            height=size.get("height") if size else None,
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
