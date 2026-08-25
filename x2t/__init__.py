"""x2t - Twitter / X Media Extractor & Downloader Engine."""

from pathlib import Path
from typing import Optional, Union

from x2t.core.extractor import XMediaExtractor
from x2t.models import MediaItem, MediaType, PostMediaResult

__version__ = "0.1.0"
__all__ = [
    "extract_media",
    "download_media",
    "download_media_async",
    "XMediaExtractor",
    "PostMediaResult",
    "MediaItem",
    "MediaType",
]

_default_extractor = XMediaExtractor()


def extract_media(url_or_id: str) -> PostMediaResult:
    """Extract all media links and metadata from a Twitter/X post without downloading."""
    return _default_extractor.extract_info(url_or_id)


def download_media(
    url_or_id: str,
    output_dir: Optional[Union[str, Path]] = None,
    progress_callback: Optional[callable] = None,
) -> PostMediaResult:
    """Extract and download all media files from a Twitter/X post."""
    return _default_extractor.download_media(
        url_or_id, output_dir=output_dir, progress_callback=progress_callback
    )


async def download_media_async(
    url_or_id: str,
    output_dir: Optional[Union[str, Path]] = None,
    progress_callback: Optional[callable] = None,
) -> PostMediaResult:
    """Asynchronously extract and download all media files from a Twitter/X post."""
    return await _default_extractor.download_media_async(
        url_or_id, output_dir=output_dir, progress_callback=progress_callback
    )
