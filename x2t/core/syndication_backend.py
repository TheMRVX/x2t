"""Direct Twitter Syndication API backend for fast fallback extraction."""

import math
from typing import Any, Dict, List, Optional
import httpx

from x2t.config import config
from x2t.models import MediaItem, MediaType, PostMediaResult
from x2t.utils.url_helper import extract_tweet_id, normalize_tweet_url
from x2t.utils.media_helper import get_orig_photo_url, select_best_video_variant


def _base36_encode(number: int) -> str:
    """Encode an integer in base 36."""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if number == 0:
        return "0"
    base36 = []
    while number:
        number, i = divmod(number, 36)
        base36.append(alphabet[i])
    return "".join(reversed(base36))


def _generate_syndication_token(tweet_id: str) -> str:
    r"""Generate Twitter syndication token used to query cdn.syndication.twimg.com.

    Formula derived from Twitter's web syndication bundle:
    (tweet_id / 1e15 * PI).toString(36).replace(/(0+|\.)/g, '')
    """
    try:
        val = (int(tweet_id) / 1e15) * math.pi
        # Represent floating point number in base 36
        # Separate integer and fractional parts
        int_part = int(val)
        frac_part = val - int_part
        
        int_str = _base36_encode(int_part)
        
        # Approximate 16 fractional digits in base 36
        frac_digits = []
        f = frac_part
        for _ in range(16):
            f *= 36
            digit = int(f)
            frac_digits.append("0123456789abcdefghijklmnopqrstuvwxyz"[digit])
            f -= digit
            
        full_str = int_str + "".join(frac_digits)
        # Remove zeros and dots
        clean = full_str.replace("0", "").replace(".", "")
        return clean
    except Exception:
        return "x"


class SyndicationBackend:
    """Directly requests Twitter's CDN syndication endpoint to extract media."""

    def __init__(self):
        self.client = httpx.Client(
            timeout=config.request_timeout,
            headers={
                "User-Agent": config.user_agent,
                "Referer": "https://platform.twitter.com/",
                "Origin": "https://platform.twitter.com",
            },
            follow_redirects=True,
        )

    def extract(self, url_or_id: str) -> PostMediaResult:
        """Extract media using Twitter's syndication endpoint."""
        tweet_id = extract_tweet_id(url_or_id)
        if not tweet_id:
            raise ValueError(f"Could not extract tweet ID from '{url_or_id}'")

        token = _generate_syndication_token(tweet_id)
        url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token={token}"

        response = self.client.get(url)
        if response.status_code == 404:
            raise RuntimeError(f"Tweet {tweet_id} not found or deleted")
        if response.status_code != 200:
            raise RuntimeError(
                f"Syndication API returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        return self._parse_tweet_data(data, tweet_id, url_or_id)

    def _parse_tweet_data(
        self, data: Dict[str, Any], tweet_id: str, original_url: str
    ) -> PostMediaResult:
        canonical_url = normalize_tweet_url(original_url)
        text = data.get("text")
        user = data.get("user", {})
        author_name = user.get("name")
        author_username = user.get("screen_name")
        created_at = data.get("created_at")

        items: List[MediaItem] = []
        media_details = data.get("mediaDetails", [])

        item_idx = 1
        for m in media_details:
            m_type = m.get("type", "")
            if m_type in ("video", "animated_gif"):
                is_gif = m_type == "animated_gif"
                video_info = m.get("video_info", {})
                variants = video_info.get("variants", [])
                
                best_variant = select_best_video_variant(variants)
                if best_variant and "url" in best_variant:
                    # Get aspect ratio
                    aspect = video_info.get("aspect_ratio", [None, None])
                    width = m.get("original_info", {}).get("width")
                    height = m.get("original_info", {}).get("height")
                    duration_ms = video_info.get("duration_millis", 0)

                    items.append(
                        MediaItem(
                            id=str(item_idx),
                            type=MediaType.GIF if is_gif else MediaType.VIDEO,
                            url=best_variant["url"],
                            width=width,
                            height=height,
                            bitrate=best_variant.get("bitrate"),
                            duration_seconds=duration_ms / 1000.0 if duration_ms else None,
                            thumbnail_url=m.get("media_url_https"),
                            is_gif=is_gif,
                        )
                    )
                    item_idx += 1
            elif m_type == "photo":
                photo_url = m.get("media_url_https") or m.get("url")
                if photo_url:
                    orig_url = get_orig_photo_url(photo_url)
                    width = m.get("original_info", {}).get("width")
                    height = m.get("original_info", {}).get("height")

                    items.append(
                        MediaItem(
                            id=str(item_idx),
                            type=MediaType.PHOTO,
                            url=orig_url,
                            width=width,
                            height=height,
                            thumbnail_url=photo_url,
                            is_gif=False,
                        )
                    )
                    item_idx += 1

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
