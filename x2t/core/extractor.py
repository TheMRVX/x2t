"""Central extractor coordinator managing backends and downloads."""

from pathlib import Path
from typing import Optional, Union

from x2t.core.downloader import MediaDownloader
from x2t.core.fxtwitter_backend import FxTwitterBackend
from x2t.core.syndication_backend import SyndicationBackend
from x2t.core.ytdlp_backend import YtdlpBackend
from x2t.exceptions import (
    AgeRestrictedError,
    ExtractionError,
    NetworkConnectionError,
    NoMediaFoundError,
    PrivateTweetError,
    TweetNotFoundError,
    TwitterRateLimitError,
)
from x2t.logger import get_logger
from x2t.models import PostMediaResult
from x2t.utils.url_helper import extract_tweet_id

logger = get_logger("x2t.extractor")


class XMediaExtractor:
    """High-level extractor coordinator supporting multi-backend extraction and downloading."""

    def __init__(self, cookies_file: Optional[str] = None):
        self.fxtwitter_backend = FxTwitterBackend()
        self.ytdlp_backend = YtdlpBackend(cookies_file=cookies_file)
        self.syndication_backend = SyndicationBackend()

    def extract_info(self, url_or_id: str) -> PostMediaResult:
        """Extract media links and metadata from an X/Twitter post without downloading.

        Tries backends in cascade:
        1. FxTwitter / VxTwitter backend (fast, handles sensitive/age-restricted media)
        2. yt-dlp native backend
        3. Direct syndication fallback backend
        """
        tweet_id = extract_tweet_id(url_or_id)
        errors = []
        parsed_empty_result = None

        # 1. Try FxTwitter / VxTwitter backend
        try:
            result = self.fxtwitter_backend.extract(url_or_id)
            if result and result.has_media:
                return result
            if result and not result.has_media:
                parsed_empty_result = result
        except Exception as e:
            logger.debug(f"FxTwitter backend error for {url_or_id}: {e}")
            errors.append(f"FxTwitter: {e}")

        # 2. Try yt-dlp backend
        try:
            result = self.ytdlp_backend.extract(url_or_id)
            if result and result.has_media:
                return result
            if result and not result.has_media and not parsed_empty_result:
                parsed_empty_result = result
        except Exception as e:
            logger.debug(f"yt-dlp backend error for {url_or_id}: {e}")
            errors.append(f"yt-dlp: {e}")

        # 3. Try syndication fallback backend
        try:
            result = self.syndication_backend.extract(url_or_id)
            if result and result.has_media:
                return result
            if result and not result.has_media and not parsed_empty_result:
                parsed_empty_result = result
        except Exception as e:
            logger.debug(f"Syndication backend error for {url_or_id}: {e}")
            errors.append(f"Syndication: {e}")

        # If a backend successfully resolved the tweet but found 0 media items
        if parsed_empty_result and not parsed_empty_result.has_media:
            return parsed_empty_result

        # Map aggregate error messages to structured domain exceptions
        combined_err = " ".join(errors).lower()
        if "404" in combined_err or "not found" in combined_err or "deleted" in combined_err:
            raise TweetNotFoundError(f"Tweet {tweet_id} not found or deleted.", tweet_id=tweet_id)
        if "private" in combined_err or "protected" in combined_err or "401" in combined_err:
            raise PrivateTweetError(f"Tweet {tweet_id} belongs to a protected account.")
        if "sensitive" in combined_err or "age" in combined_err or "nsfw" in combined_err:
            raise AgeRestrictedError(f"Tweet {tweet_id} is age-restricted.")
        if "429" in combined_err or "rate limit" in combined_err or "too many requests" in combined_err:
            raise TwitterRateLimitError(f"Rate limit reached for tweet {tweet_id}.")
        if "timeout" in combined_err or "connect" in combined_err or "name resolution" in combined_err:
            raise NetworkConnectionError(f"Network error while fetching tweet {tweet_id}: {combined_err}")

        error_msg = "; ".join(errors) if errors else "No media found in the specified tweet"
        raise ExtractionError(
            message=f"Failed to extract media from {url_or_id}. {error_msg}",
            error_code="BACKEND_RESOLUTION_FAILED",
        )

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
