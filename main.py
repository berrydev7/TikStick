#!/usr/bin/env python3
"""Berry TikTok Sticker Scraper

A modern, interactive CLI tool to scrape sticker attachments from TikTok comments.
Saves results automatically to JSON in the script directory.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import APP_NAME, APP_VERSION, SCRIPT_DIR
from core.comment_parser import parse_comment_response
from core.exporter import (
    build_output_payload,
    generate_output_filename,
    list_previous_exports,
    load_json_file,
    resolve_non_colliding_path,
    write_json_file,
)
from core.sticker_detector import extract_stickers_from_comment
from core.sticker_downloader import download_from_json_file
from core.tiktok_client import (
    TikTokAPIError,
    TikTokClient,
    TikTokError,
    TikTokNetworkError,
    TikTokURLInvalidError,
)
from utils.cli_ui import (
    clear_screen,
    display_header,
    display_previous_results_table,
    display_scraping_summary,
    display_stickers_table,
    pause_and_return,
    prompt_menu_choice,
    prompt_text,
)
from utils.logger import init_console, logger, set_no_color
from utils.validators import is_valid_http_url, sanitize_error_message


def run_scraper(
    video_url_or_id: str,
    output_path: Optional[Path] = None,
    max_comments: Optional[int] = None,
    client: Optional[TikTokClient] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Execute the sticker scraping workflow with automatic JSON export.

    Guarantees that JSON is saved even if errors occur (partial or failed status).
    """
    started_at = datetime.now().astimezone()

    # Determine default or custom output path
    if output_path is not None:
        target_file = Path(output_path).resolve()
    else:
        # Default: Always save in SCRIPT_DIR, never working directory
        base_name = generate_output_filename(started_at)
        target_file = resolve_non_colliding_path(SCRIPT_DIR, base_name)

    logger.info("Validating video URL...")

    tik_client = client or TikTokClient()
    canonical_url: Optional[str] = None
    video_id: Optional[str] = None

    stickers: List[Dict[str, Any]] = []
    comments_processed = 0
    errors: List[str] = []
    status = "completed"

    try:
        canonical_url, video_id = tik_client.resolve_video(video_url_or_id)
        logger.info("Initializing scraper...")
        logger.info("Retrieving accessible comments...")
        logger.info("Detecting sticker attachments...")

        # Setup progress indicator
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
        )
        from utils.logger import get_console

        console = get_console()

        with Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[cyan]{task.description}[/cyan]"),
            BarColumn(bar_width=38, style="dim cyan", complete_style="bold cyan"),
            TextColumn("[dim]{task.fields[status_info]}[/dim]"),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                "Progress",
                total=None,
                status_info="Fetching comments...",
            )

            unique_sticker_keys = set()
            direct_urls_count = 0

            try:
                for comment in tik_client.iterate_comments(video_id=video_id, max_comments=max_comments):
                    comments_processed += 1

                    # Detect stickers in this comment
                    found = extract_stickers_from_comment(comment)
                    if found:
                        for s in found:
                            stickers.append(s)
                            s_key = s.get("sticker_id") or s.get("sticker_url")
                            if s_key:
                                unique_sticker_keys.add(s_key)
                            if s.get("sticker_url") and is_valid_http_url(s.get("sticker_url")):
                                direct_urls_count += 1

                    # Update progress display
                    status_str = (
                        f"Processed: {comments_processed} | "
                        f"Stickers: {len(stickers)} | "
                        f"Unique: {len(unique_sticker_keys)}"
                    )
                    progress.update(task, status_info=status_str)

                # Set progress to 100% on complete
                progress.update(task, total=100, completed=100, status_info="Completed.")

            except (TikTokError, Exception) as scrape_err:
                error_msg = sanitize_error_message(scrape_err)
                errors.append(error_msg)
                status = "partial" if (comments_processed > 0 or len(stickers) > 0) else "failed"
                logger.warning(f"Scraping interrupted: {error_msg}")

    except (TikTokError, Exception) as init_err:
        error_msg = sanitize_error_message(init_err)
        errors.append(error_msg)
        status = "failed"
        logger.error(f"Scraper initialization error: {error_msg}")

    # Finalize timestamps and payload
    completed_at = datetime.now().astimezone()

    payload = build_output_payload(
        video_url=canonical_url or video_url_or_id,
        video_id=video_id,
        started_at=started_at,
        completed_at=completed_at,
        comments_processed=comments_processed,
        stickers=stickers,
        errors=errors,
        status=status,
    )

    # Save to disk
    write_json_file(payload, target_file)

    # Display summary
    unique_count = len({s.get("sticker_id") or s.get("sticker_url") for s in stickers if (s.get("sticker_id") or s.get("sticker_url"))})
    direct_count = len([s for s in stickers if s.get("sticker_url") and is_valid_http_url(s.get("sticker_url"))])

    display_scraping_summary(
        video_id=video_id or "N/A",
        comments_processed=comments_processed,
        stickers_found=len(stickers),
        unique_stickers=unique_count,
        direct_urls_found=direct_count,
        json_path=target_file,
    )

    if status == "completed":
        logger.success("Scraping completed.")
    elif status == "partial":
        logger.warning(f"Scraping completed partially with {len(stickers)} stickers.")
    else:
        logger.error("Scraping failed. Error metadata saved to JSON.")

    logger.info(f"JSON File : {target_file}")

    return target_file, payload


def handle_extract_json(file_path_str: str) -> None:
    """Extract and display sticker URLs from an existing JSON file."""
    path = Path(file_path_str).resolve()
    logger.info(f"Reading JSON file: {path}")

    try:
        data = load_json_file(path)
    except Exception as e:
        logger.error(f"Failed to read JSON: {e}")
        return

    stickers = data.get("stickers", [])
    if not stickers:
        logger.warning("No stickers found in this JSON file.")
        return

    display_stickers_table(stickers, title=f"EXTRACTED FROM {path.name}")
    valid_urls = [s["sticker_url"] for s in stickers if s.get("sticker_url") and is_valid_http_url(s.get("sticker_url"))]
    logger.success(f"Found {len(stickers)} stickers ({len(valid_urls)} with valid direct URLs).")


def handle_download_json(file_path_str: str, custom_output_dir: Optional[str] = None) -> None:
    """Download sticker assets from an existing JSON file."""
    path = Path(file_path_str).resolve()
    logger.info(f"Reading JSON file for download: {path}")

    target_dir = Path(custom_output_dir).resolve() if custom_output_dir else None

    try:
        summary = download_from_json_file(path, target_dir=target_dir)
        logger.success("Download process finished.")
        logger.info(f"Destination : {summary['output_dir']}")
        logger.info(f"Downloaded  : {summary['downloaded']}")
        logger.info(f"Failed      : {summary['failed']}")
        logger.info(f"Skipped     : {summary['skipped']}")
    except Exception as e:
        logger.error(f"Download failed: {e}")


def handle_view_previous() -> None:
    """Display previous exports and allow interactive inspection."""
    files = list_previous_exports()
    display_previous_results_table(files)

    if not files:
        return

    choice = prompt_text("Enter file number to inspect (or press Enter to return):")
    if not choice:
        return

    try:
        idx = int(choice)
        if 1 <= idx <= len(files):
            selected = files[idx - 1]
            handle_extract_json(str(selected))
        else:
            logger.warning("Invalid item number.")
    except ValueError:
        logger.warning("Please enter a valid number.")


def interactive_main() -> None:
    """Main interactive menu loop with clean screen refreshes."""
    clear_screen()
    display_header()

    while True:
        choice = prompt_menu_choice()

        if choice == "1":
            # Scrape stickers from TikTok video
            url = prompt_text("TikTok Video URL:")
            if not url:
                logger.warning("No URL provided. Returning to menu.")
                pause_and_return()
                display_header(clear=True)
                continue

            try:
                run_scraper(url)
            except KeyboardInterrupt:
                logger.warning("\nScraping canceled by user.")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

            pause_and_return()
            display_header(clear=True)

        elif choice == "2":
            # Extract sticker URLs from JSON
            json_file = prompt_text("JSON file path:")
            if not json_file:
                logger.warning("No file path provided.")
                pause_and_return()
                display_header(clear=True)
                continue
            handle_extract_json(json_file)
            pause_and_return()
            display_header(clear=True)

        elif choice == "3":
            # Download stickers from JSON
            json_file = prompt_text("JSON file path:")
            if not json_file:
                logger.warning("No file path provided.")
                pause_and_return()
                display_header(clear=True)
                continue
            handle_download_json(json_file)
            pause_and_return()
            display_header(clear=True)

        elif choice == "4":
            # View previous results
            handle_view_previous()
            pause_and_return()
            display_header(clear=True)

        elif choice == "5":
            # Exit
            clear_screen()
            logger.info("Thank you for using Berry TikTok Sticker Scraper. Goodbye!")
            sys.exit(0)

        else:
            logger.warning("Invalid choice. Please select an option from 1 to 5.")
            pause_and_return()
            display_header(clear=True)


def parse_arguments() -> argparse.Namespace:
    """Configure and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="berry",
        description=f"{APP_NAME} v{APP_VERSION} - Scrape, extract, and download TikTok comment stickers.",
    )

    parser.add_argument(
        "--url",
        type=str,
        help="TikTok video URL or numerical ID to scrape directly without interactive menu.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Custom output JSON path (defaults to script directory).",
    )
    parser.add_argument(
        "--extract-json",
        type=str,
        metavar="JSON_FILE",
        help="Extract and display sticker URLs from an existing JSON export.",
    )
    parser.add_argument(
        "--download-json",
        type=str,
        metavar="JSON_FILE",
        help="Download stickers whose media URLs are present in the JSON export.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable terminal colors and rich styling.",
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=None,
        help="Optional limit on number of comments to process.",
    )

    return parser.parse_args()


def main() -> None:
    """Application entry point."""
    args = parse_arguments()

    if args.no_color:
        set_no_color(True)
    else:
        init_console(no_color=False)

    # If any specific action flag is provided, run non-interactively
    if args.url:
        output_p = Path(args.output).resolve() if args.output else None
        try:
            run_scraper(
                video_url_or_id=args.url,
                output_path=output_p,
                max_comments=args.max_comments,
            )
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)

    elif args.extract_json:
        handle_extract_json(args.extract_json)

    elif args.download_json:
        output_dir = args.output if args.output else None
        handle_download_json(args.download_json, custom_output_dir=output_dir)

    else:
        # No CLI arguments -> run interactive menu
        try:
            interactive_main()
        except (KeyboardInterrupt, EOFError):
            logger.info("\nExiting. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
