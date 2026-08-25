"""Central extractor coordinator managing multi-backend cascades, TTL caching, and downloads."""

import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

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
    """High-level extractor coordinator supporting multi-backend cascades and smart TTL caching."""

    def __init__(self, cookies_file: Optional[str] = None, cache_ttl_seconds: float = 300.0):
        self.fxtwitter_backend = FxTwitterBackend()
        self.ytdlp_backend = YtdlpBackend(cookies_file=cookies_file)
        self.syndication_backend = SyndicationBackend()
        self.cache_ttl_seconds = cache_ttl_seconds
        # In-memory TTL cache: tweet_id -> (PostMediaResult, expire_timestamp)
        self._cache: Dict[str, Tuple[PostMediaResult, float]] = {}

    def _get_from_cache(self, tweet_id: str) -> Optional[PostMediaResult]:
        """Retrieve post result from in-memory TTL cache if not expired."""
        if tweet_id in self._cache:
            result, expire_at = self._cache[tweet_id]
            if time.time() < expire_at:
                logger.debug(f"TTL Cache HIT for tweet_id: {tweet_id}")
                return result.model_copy(deep=True)
            else:
                del self._cache[tweet_id]
        return None

    def _save_to_cache(self, tweet_id: str, result: PostMediaResult):
        """Save post result to in-memory TTL cache."""
        if tweet_id and result:
            expire_at = time.time() + self.cache_ttl_seconds
            self._cache[tweet_id] = (result.model_copy(deep=True), expire_at)

    def clear_cache(self):
        """Clear all entries in the TTL cache."""
        self._cache.clear()

    def extract_info(self, url_or_id: str, use_cache: bool = True) -> PostMediaResult:
        """Extract media links and metadata from an X/Twitter post without downloading.

        Tries backends in cascade:
        1. Memory TTL Cache (instant response for duplicate requests)
        2. FxTwitter / VxTwitter backend (fast, handles sensitive/age-restricted media)
        3. yt-dlp native backend
        4. Direct syndication fallback backend
        """
        tweet_id = extract_tweet_id(url_or_id)

        # 0. Check TTL Cache
        if use_cache and tweet_id:
            cached = self._get_from_cache(tweet_id)
            if cached is not None:
                return cached

        errors = []
        parsed_empty_result = None

        # 1. Try FxTwitter / VxTwitter backend
        try:
            result = self.fxtwitter_backend.extract(url_or_id)
            if result and result.has_media:
                if use_cache and tweet_id:
                    self._save_to_cache(tweet_id, result)
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
                if use_cache and tweet_id:
                    self._save_to_cache(tweet_id, result)
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
                if use_cache and tweet_id:
                    self._save_to_cache(tweet_id, result)
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
