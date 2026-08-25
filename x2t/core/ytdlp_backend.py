"""yt-dlp based extractor backend for X / Twitter."""

from typing import Any, Dict, List, Optional
import yt_dlp

from x2t.config import config
from x2t.models import MediaItem, MediaType, PostMediaResult
from x2t.utils.url_helper import normalize_tweet_url, extract_tweet_id
from x2t.utils.media_helper import get_orig_photo_url


class YtdlpBackend:
    """Extracts media from Twitter/X using yt-dlp's native extractor."""

    def __init__(self, cookies_file: Optional[str] = None):
        self.cookies_file = cookies_file

    def _get_ydl_opts(self) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "quiet": config.ytdlp_quiet,
            "no_warnings": config.ytdlp_no_warnings,
            "extract_flat": False,
            "skip_download": True,
            "http_headers": {
                "User-Agent": config.user_agent,
            },
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        return opts

    def extract(self, url_or_id: str) -> PostMediaResult:
        """Extract media metadata and direct links using yt-dlp."""
        tweet_id = extract_tweet_id(url_or_id)
        if not tweet_id:
            raise ValueError(f"Could not extract tweet ID from '{url_or_id}'")

        canonical_url = normalize_tweet_url(url_or_id)
        ydl_opts = self._get_ydl_opts()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(canonical_url, download=False)
            if not info:
                raise RuntimeError(f"Failed to extract info for {canonical_url}")

            # Check if this is a playlist/multi-video entry or single entry
            raw_entries = info.get("entries")
            if raw_entries:
                entries = [e for e in raw_entries if e is not None]
            else:
                entries = [info]

            items: List[MediaItem] = []
            author_name = info.get("uploader") or info.get("channel")
            author_username = info.get("uploader_id") or info.get("channel_id")
            tweet_text = info.get("description") or info.get("title")
            created_at = str(info.get("timestamp") or info.get("upload_date") or "")

            item_idx = 1
            for entry in entries:
                formats = entry.get("formats", [])
                thumbnails = entry.get("thumbnails", [])

                # Exclude audio-only formats (where vcodec is explicitly 'none' or format_id starts with hls-audio)
                non_audio_formats = [
                    f for f in formats
                    if f.get("vcodec") != "none"
                    and not str(f.get("format_id", "")).startswith("hls-audio")
                    and f.get("url")
                ]

                # Separate direct progressive MP4 vs HLS m3u8
                direct_mp4s = [
                    f for f in non_audio_formats
                    if ".m3u8" not in f.get("url", "")
                    and f.get("protocol") in ("http", "https", "http_dash_segments", None)
                ]

                selected_format = None
                if direct_mp4s:
                    # Prefer highest bitrate / highest height direct MP4
                    selected_format = max(
                        direct_mp4s,
                        key=lambda f: (
                            f.get("height") or 0,
                            f.get("tbr") or f.get("vbr") or 0,
                        ),
                    )
                elif non_audio_formats:
                    # Fallback to HLS m3u8 format
                    selected_format = max(
                        non_audio_formats,
                        key=lambda f: (
                            f.get("height") or 0,
                            f.get("tbr") or f.get("vbr") or 0,
                        ),
                    )

                if selected_format:
                    # Check if GIF or regular video
                    has_audio = (
                        selected_format.get("acodec") not in (None, "none")
                        or any(
                            f.get("acodec") not in (None, "none")
                            and not str(f.get("format_id", "")).startswith("hls-audio")
                            for f in formats
                        )
                    )
                    # GIFs on Twitter have duration <= 60s and no audio track
                    is_gif = not has_audio and (entry.get("duration", 0) <= 60)
                    media_type = MediaType.GIF if is_gif else MediaType.VIDEO

                    thumb = entry.get("thumbnail")
                    if not thumb and thumbnails:
                        thumb = thumbnails[-1].get("url")

                    # If dimensions missing from format, try finding in format_id or thumbnails
                    width = selected_format.get("width")
                    height = selected_format.get("height")
                    if not width or not height:
                        if thumbnails:
                            width = thumbnails[-1].get("width")
                            height = thumbnails[-1].get("height")

                    items.append(
                        MediaItem(
                            id=str(item_idx),
                            type=media_type,
                            url=selected_format["url"],
                            width=width,
                            height=height,
                            bitrate=int(selected_format.get("tbr") * 1000) if selected_format.get("tbr") else None,
                            duration_seconds=entry.get("duration"),
                            thumbnail_url=thumb,
                            is_gif=is_gif,
                        )
                    )
                    item_idx += 1
                elif thumbnails:
                    # Photo entry
                    best_thumb = thumbnails[-1].get("url")
                    if best_thumb:
                        orig_url = get_orig_photo_url(best_thumb)
                        items.append(
                            MediaItem(
                                id=str(item_idx),
                                type=MediaType.PHOTO,
                                url=orig_url,
                                width=thumbnails[-1].get("width"),
                                height=thumbnails[-1].get("height"),
                                thumbnail_url=best_thumb,
                                is_gif=False,
                            )
                        )
                        item_idx += 1

            return PostMediaResult(
                tweet_id=tweet_id,
                original_url=url_or_id,
                canonical_url=canonical_url,
                text=tweet_text,
                author_name=author_name,
                author_username=author_username,
                items=items,
                created_at=created_at or None,
            )
