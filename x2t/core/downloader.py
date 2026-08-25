"""Media file downloader supporting synchronous and asynchronous downloads with FFmpeg HLS handling."""

import asyncio
from pathlib import Path
import subprocess
from typing import Optional, Union
import httpx

from x2t.config import config
from x2t.models import MediaItem, PostMediaResult
from x2t.utils.media_helper import generate_filename


class MediaDownloader:
    """Handles downloading media assets from Twitter to local disk."""

    def __init__(self, download_dir: Optional[Union[str, Path]] = None):
        self.download_dir = Path(download_dir) if download_dir else config.default_download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _download_m3u8_stream(self, url: str, dest_path: Path) -> int:
        """Download an HLS (.m3u8) video stream using FFmpeg."""
        cmd = [
            "ffmpeg",
            "-y",
            "-nostats",
            "-loglevel", "error",
            "-headers", f"User-Agent: {config.user_agent}\r\n",
            "-i", url,
            "-c", "copy",
            str(dest_path.resolve()),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with exit code {proc.returncode}: {stderr.decode()}")

        if dest_path.exists():
            return dest_path.stat().st_size
        return 0

    async def _download_item_async(
        self, client: httpx.AsyncClient, item: MediaItem, tweet_id: str, index: int
    ) -> MediaItem:
        """Download a single media item asynchronously."""
        # Determine file extension
        ext = "mp4" if item.is_gif or item.type.value in ("video", "animated_gif") else "jpg"
        if ".png" in item.url.lower():
            ext = "png"
        elif ".webp" in item.url.lower():
            ext = "webp"

        filename = generate_filename(tweet_id, index, item.type, ext)
        dest_path = self.download_dir / filename

        # Check if URL is an HLS playlist
        if ".m3u8" in item.url:
            total_bytes = await self._download_m3u8_stream(item.url, dest_path)
        else:
            async with client.stream("GET", item.url) as response:
                response.raise_for_status()
                total_bytes = 0
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        total_bytes += len(chunk)

        item.local_path = str(dest_path.resolve())
        item.filename = filename
        item.size_bytes = total_bytes
        return item

    async def download_post_async(
        self, result: PostMediaResult, progress_callback: Optional[callable] = None
    ) -> PostMediaResult:
        """Download all media items for a post concurrently."""
        if not result.items:
            return result

        limits = httpx.Limits(max_connections=config.max_concurrent_downloads)
        async with httpx.AsyncClient(
            timeout=config.request_timeout,
            limits=limits,
            headers={"User-Agent": config.user_agent},
            follow_redirects=True,
        ) as client:
            tasks = [
                self._download_item_async(client, item, result.tweet_id, idx + 1)
                for idx, item in enumerate(result.items)
            ]
            downloaded_items = await asyncio.gather(*tasks)
            result.items = list(downloaded_items)

        if progress_callback:
            progress_callback(result)

        return result

    def download_post(
        self, result: PostMediaResult, progress_callback: Optional[callable] = None
    ) -> PostMediaResult:
        """Synchronous wrapper to download all post media."""
        return asyncio.run(self.download_post_async(result, progress_callback))
