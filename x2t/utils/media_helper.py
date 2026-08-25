"""Media URL and format utilities for Twitter media assets."""

import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from x2t.models import MediaType

# MTProto allows up to 2000 MB (2 GB) uploads
DEFAULT_MAX_FILE_SIZE = 2000 * 1024 * 1024


def get_orig_photo_url(photo_url: str) -> str:
    """Ensure a Twitter photo URL downloads in highest original quality (name=orig)."""
    parsed = urlparse(photo_url)
    if "pbs.twimg.com" not in parsed.netloc:
        return photo_url

    query = parse_qs(parsed.query)
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


def select_best_video_variant(
    variants: List[Dict],
    duration_seconds: Optional[float] = None,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
) -> Optional[Dict]:
    """Select the highest bitrate MP4 variant that fits within max_size_bytes."""
    mp4_variants = [
        v for v in variants
        if v.get("content_type") == "video/mp4" and "url" in v
    ]
    if not mp4_variants:
        return None

    # Sort descending by bitrate
    sorted_variants = sorted(mp4_variants, key=lambda x: x.get("bitrate", 0), reverse=True)

    if duration_seconds and duration_seconds > 0:
        # Estimate size: (bitrate * duration) / 8
        for v in sorted_variants:
            bitrate = v.get("bitrate", 0)
            if bitrate:
                est_size = (bitrate * duration_seconds) / 8
                if est_size <= max_size_bytes:
                    return v

    return sorted_variants[0]


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
