"""Command-line interface (CLI) for x2t."""

import argparse
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from x2t.core.extractor import XMediaExtractor
from x2t.models import MediaType


def format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def main():
    parser = argparse.ArgumentParser(
        prog="x2t",
        description="Extract and download all media (videos, gifs, photos) from X / Twitter posts.",
    )
    parser.add_argument("url", help="Twitter / X post URL or tweet ID")
    parser.add_argument(
        "-d", "--download",
        action="store_true",
        help="Download the extracted media files to local disk",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="./downloads",
        help="Output directory for downloaded media (default: ./downloads)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as structured JSON",
    )
    parser.add_argument(
        "-c", "--cookies",
        type=str,
        default=None,
        help="Path to cookies file (e.g., cookies.txt) for protected tweets",
    )

    args = parser.parse_args()
    console = Console()

    extractor = XMediaExtractor(cookies_file=args.cookies)

    try:
        if args.download:
            with console.status("[bold green]Extracting and downloading media...[/bold green]"):
                result = extractor.download_media(args.url, output_dir=args.output)
        else:
            with console.status("[bold blue]Extracting tweet media info...[/bold blue]"):
                result = extractor.extract_info(args.url)

        if args.json:
            print(result.model_dump_json(indent=2))
            return

        # Render pretty output with Rich
        panel_content = (
            f"[bold cyan]Author:[/bold cyan] {result.author_name or 'N/A'} (@{result.author_username or 'N/A'})\n"
            f"[bold cyan]Tweet ID:[/bold cyan] {result.tweet_id}\n"
            f"[bold cyan]URL:[/bold cyan] {result.canonical_url}\n"
            f"[bold cyan]Media Count:[/bold cyan] {result.media_count} "
            f"([green]{result.video_count} videos[/green], "
            f"[yellow]{result.gif_count} gifs[/yellow], "
            f"[magenta]{result.photo_count} photos[/magenta])\n"
        )
        if result.text:
            panel_content += f"\n[bold]Tweet Text:[/bold]\n{result.text[:200]}"
            if len(result.text) > 200:
                panel_content += "..."

        console.print(Panel(panel_content, title="[bold white on blue] X2T Tweet Media Extractor [/bold white on blue]", expand=False))

        if not result.has_media:
            console.print("[yellow]No media items found in this post.[/yellow]")
            return

        table = Table(title="Extracted Media Items")
        table.add_column("#", justify="center", style="cyan")
        table.add_column("Type", justify="center")
        table.add_column("Resolution / Dimensions", justify="center")
        table.add_column("Duration", justify="center")
        table.add_column("Status", justify="left")

        for idx, item in enumerate(result.items, start=1):
            type_badge = (
                "[bold yellow]GIF (MP4)[/bold yellow]"
                if item.type == MediaType.GIF
                else ("[bold green]VIDEO[/bold green]" if item.type == MediaType.VIDEO else "[bold magenta]PHOTO[/bold magenta]")
            )
            res_str = item.resolution or "N/A"
            dur_str = f"{item.duration_seconds:.1f}s" if item.duration_seconds else "-"

            if item.is_downloaded:
                size_str = format_bytes(item.size_bytes) if item.size_bytes else ""
                status_str = f"[bold green]✓ Downloaded[/bold green] ({item.filename} - {size_str})\n[dim]{item.local_path}[/dim]"
            else:
                status_str = f"[dim]{item.url[:60]}...[/dim]"

            table.add_row(str(idx), type_badge, res_str, dur_str, status_str)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
