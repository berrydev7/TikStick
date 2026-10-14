"""Sticker downloader module for downloading media assets from JSON."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from config import DEFAULT_HEADERS, DEFAULT_TIMEOUT
from core.exporter import write_json_file
from utils.cli_ui import create_download_progress
from utils.logger import logger
from utils.validators import is_valid_http_url, sanitize_filename


def get_extension_for_media_type(media_type: Optional[str], url: Optional[str]) -> str:
    """Determine file extension from media type or URL."""
    mt = (media_type or "").lower()
    if "gif" in mt:
        return ".gif"
    if "png" in mt:
        return ".png"
    if "jpeg" in mt or "jpg" in mt:
        return ".jpg"
    if "webp" in mt:
        return ".webp"

    if url:
        url_lower = url.lower()
        if ".gif" in url_lower:
            return ".gif"
        if ".png" in url_lower:
            return ".png"
        if ".jpg" in url_lower or ".jpeg" in url_lower:
            return ".jpg"
        if ".webp" in url_lower:
            return ".webp"

    return ".webp"


def download_stickers_from_list(
    stickers: List[Dict[str, Any]],
    output_dir: Path,
    session: Optional[requests.Session] = None,
    timeout: float = DEFAULT_TIMEOUT,
    show_progress: bool = True,
) -> Dict[str, Any]:
    """Download sticker files to output_dir and update download_status."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)

    valid_stickers = [
        s for s in stickers if s.get("sticker_url") and is_valid_http_url(s.get("sticker_url"))
    ]

    total = len(valid_stickers)
    downloaded = 0
    failed = 0
    skipped = len(stickers) - total

    if total == 0:
        return {
            "total": len(stickers),
            "downloaded": 0,
            "failed": 0,
            "skipped": skipped,
            "output_dir": output_dir,
        }

    progress = create_download_progress() if show_progress else None

    if progress:
        progress.start()
        task_id = progress.add_task("Downloading stickers...", total=total)

    try:
        for idx, sticker in enumerate(valid_stickers, 1):
            url = sticker["sticker_url"]
            s_id = sticker.get("sticker_id") or "unnamed"
            m_type = sticker.get("media_type")
            ext = get_extension_for_media_type(m_type, url)

            # Generate unique local filename
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
            safe_id = sanitize_filename(str(s_id))
            filename = f"sticker_{safe_id}_{url_hash}{ext}"
            file_path = output_dir / filename

            try:
                resp = sess.get(url, stream=True, timeout=timeout)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    sticker["download_status"] = "downloaded"
                    sticker["local_path"] = str(file_path)
                    downloaded += 1
                else:
                    sticker["download_status"] = "failed"
                    sticker["download_error"] = f"HTTP {resp.status_code}"
                    failed += 1
            except Exception as e:
                sticker["download_status"] = "failed"
                sticker["download_error"] = str(e)
                failed += 1

            if progress:
                progress.advance(task_id)

    finally:
        if progress:
            progress.stop()

    return {
        "total": len(stickers),
        "downloaded": downloaded,
        "failed": failed,
        "skipped": skipped,
        "output_dir": output_dir,
    }


def download_from_json_file(
    json_path: Path,
    target_dir: Optional[Path] = None,
    save_updated_json: bool = True,
) -> Dict[str, Any]:
    """Load JSON file, download all valid stickers, and optionally save updated status."""
    import json

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stickers = data.get("stickers", [])
    if not isinstance(stickers, list):
        raise ValueError("Invalid JSON format: 'stickers' key is missing or not a list")

    if target_dir is None:
        # Default: folder named stickers_<json_stem> in same directory as JSON
        target_dir = json_path.parent / f"stickers_{json_path.stem}"

    summary = download_stickers_from_list(stickers, output_dir=target_dir)

    if save_updated_json:
        # Write back updated download_status to the json file
        write_json_file(data, json_path)

    return summary
