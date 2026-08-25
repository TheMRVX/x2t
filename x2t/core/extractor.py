"""Central extractor coordinator managing backends and downloads."""

import logging
from pathlib import Path
from typing import Optional, Union

from x2t.core.downloader import MediaDownloader
from x2t.core.fxtwitter_backend import FxTwitterBackend
from x2t.core.syndication_backend import SyndicationBackend
from x2t.core.ytdlp_backend import YtdlpBackend
from x2t.models import PostMediaResult

logger = logging.getLogger("x2t")


class XMediaExtractor:
    """High-level extractor coordinator supporting multi-backend extraction and downloading."""

    def __init__(self, cookies_file: Optional[str] = None):
        self.fxtwitter_backend = FxTwitterBackend()
        self.ytdlp_backend = YtdlpBackend(cookies_file=cookies_file)
        self.syndication_backend = SyndicationBackend()

    def extract_info(self, url_or_id: str) -> PostMediaResult:
        """Extract media links and metadata from an X/Twitter post without downloading.

        Tries:
        1. FxTwitter / VxTwitter backend (fast, handles sensitive/age-restricted media)
        2. yt-dlp native backend
        3. Direct syndication fallback backend
        """
        errors = []

        # 1. Try FxTwitter / VxTwitter backend
        try:
            result = self.fxtwitter_backend.extract(url_or_id)
            if result and result.has_media:
                return result
        except Exception as e:
            logger.debug(f"FxTwitter backend failed: {e}")
            errors.append(f"FxTwitter: {e}")

        # 2. Try yt-dlp backend
        try:
            result = self.ytdlp_backend.extract(url_or_id)
            if result and result.has_media:
                return result
        except Exception as e:
            logger.debug(f"yt-dlp backend failed: {e}")
            errors.append(f"yt-dlp: {e}")

        # 3. Try syndication fallback backend
        try:
            result = self.syndication_backend.extract(url_or_id)
            if result and result.has_media:
                return result
        except Exception as e:
            logger.debug(f"Syndication backend failed: {e}")
            errors.append(f"Syndication: {e}")

        # If all backends failed or no media found
        error_msg = "; ".join(errors) if errors else "No media found in the specified tweet"
        raise RuntimeError(f"Failed to extract media from {url_or_id}. Errors: {error_msg}")

    def download_media(
        self,
        url_or_id: str,
        output_dir: Optional[Union[str, Path]] = None,
        progress_callback: Optional[callable] = None,
    ) -> PostMediaResult:
        """Extract and download all media from an X/Twitter post to disk."""
        result = self.extract_info(url_or_id)
        if not result.has_media:
            return result

        downloader = MediaDownloader(download_dir=output_dir)
        return downloader.download_post(result, progress_callback=progress_callback)

    async def download_media_async(
        self,
        url_or_id: str,
        output_dir: Optional[Union[str, Path]] = None,
        progress_callback: Optional[callable] = None,
    ) -> PostMediaResult:
        """Asynchronously extract and download all media from an X/Twitter post."""
        result = self.extract_info(url_or_id)
        if not result.has_media:
            return result

        downloader = MediaDownloader(download_dir=output_dir)
        return await downloader.download_post_async(result, progress_callback=progress_callback)
