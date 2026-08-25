"""Media URL and format utilities for Twitter media assets."""

import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from x2t.models import MediaType


def get_orig_photo_url(photo_url: str) -> str:
    """Ensure a Twitter photo URL downloads in highest original quality (name=orig).

    Example:
        https://pbs.twimg.com/media/XYZ.jpg -> https://pbs.twimg.com/media/XYZ?format=jpg&name=orig
    """
    parsed = urlparse(photo_url)
    if "pbs.twimg.com" not in parsed.netloc:
        return photo_url

    query = parse_qs(parsed.query)

    # If it's something like /media/xyz.jpg
    path = parsed.path
    ext_match = re.search(r"\.(jpg|jpeg|png|webp)$", path, re.IGNORECASE)
    if ext_match and "format" not in query:
        ext = ext_match.group(1).lower()
        if ext == "jpeg":
            ext = "jpg"
        path_without_ext = path[: ext_match.start()]
        query["format"] = [ext]
        parsed = parsed._replace(path=path_without_ext)

    query["name"] = ["orig"]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def select_best_video_variant(variants: List[Dict]) -> Optional[Dict]:
    """Select the highest bitrate / highest resolution MP4 variant from Twitter API variants."""
    mp4_variants = [
        v for v in variants
        if v.get("content_type") == "video/mp4" and "url" in v
    ]
    if not mp4_variants:
        return None

    # Sort by bitrate descending (or 0 if missing)
    return max(mp4_variants, key=lambda x: x.get("bitrate", 0))


def generate_filename(tweet_id: str, index: int, media_type: MediaType, ext: Optional[str] = None) -> str:
    """Generate standardized filename for a downloaded media item."""
    if not ext:
        if media_type in (MediaType.VIDEO, MediaType.GIF):
            ext = "mp4"
        else:
            ext = "jpg"
    ext = ext.lstrip(".")
    type_str = "gif" if media_type == MediaType.GIF else ("video" if media_type == MediaType.VIDEO else "photo")
    return f"tweet_{tweet_id}_{type_str}_{index}.{ext}"
