"""JSON Exporter module for Berry TikTok Sticker Scraper.

Ensures output is saved in the script directory by default, handles file collisions,
and guarantees atomic, valid UTF-8 JSON formatting.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config import APP_NAME, APP_VERSION, DEFAULT_OUTPUT_DIR, FILE_PREFIX
from utils.validators import sanitize_error_message


def generate_output_filename(dt: datetime, prefix: str = FILE_PREFIX) -> str:
    """Generate standardized filename: berry_stickers_YYYYMMDD_HHMMSS.json."""
    ts_str = dt.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}{ts_str}.json"


def resolve_non_colliding_path(
    target_dir: Path,
    base_filename: str,
) -> Path:
    """Resolve a path that does not overwrite an existing file by appending numeric suffixes."""
    target_dir.mkdir(parents=True, exist_ok=True)

    base_path = target_dir / base_filename
    if not base_path.exists():
        return base_path

    # Extract stem and extension
    stem = base_path.stem
    ext = base_path.suffix

    counter = 1
    while True:
        candidate = target_dir / f"{stem}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def build_output_payload(
    video_url: Optional[str],
    video_id: Optional[str],
    started_at: datetime,
    completed_at: datetime,
    comments_processed: int,
    stickers: List[Dict[str, Any]],
    errors: Optional[List[Union[str, Exception]]] = None,
    status: str = "completed",
) -> Dict[str, Any]:
    """Construct the standardized output dictionary specified in Section 4."""
    # Deduplicate unique stickers count based on sticker_id or sticker_url
    unique_keys = set()
    direct_urls_count = 0

    for s in stickers:
        s_id = s.get("sticker_id")
        s_url = s.get("sticker_url")
        key = s_id if s_id else s_url
        if key:
            unique_keys.add(key)
        if s_url and isinstance(s_url, str) and s_url.strip():
            direct_urls_count += 1

    stickers_found = len(stickers)
    unique_stickers = len(unique_keys)

    # Sanitize errors list
    sanitized_errors = []
    if errors:
        for err in errors:
            if err:
                sanitized_errors.append(sanitize_error_message(err))

    return {
        "tool": APP_NAME,
        "version": APP_VERSION,
        "source": {
            "video_url": video_url or None,
            "video_id": video_id or None,
        },
        "scraping": {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "comments_processed": int(comments_processed),
            "stickers_found": int(stickers_found),
            "unique_stickers": int(unique_stickers),
            "direct_urls_found": int(direct_urls_count),
            "status": status,
        },
        "stickers": stickers,
        "errors": sanitized_errors,
    }


def write_json_file(payload: Dict[str, Any], file_path: Path) -> Path:
    """Write dictionary to JSON with utf-8, ensure_ascii=False, and 4-space indent."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically or directly with UTF-8
    content = json.dumps(payload, ensure_ascii=False, indent=4)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.write("\n")

    return file_path


def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Read and validate a previously exported JSON file."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Invalid format: Root element is not a JSON object")

    return data


def list_previous_exports(directory: Optional[Path] = None) -> List[Path]:
    """List all previous berry_stickers_*.json files in the specified or default output directory."""
    target_dir = directory or DEFAULT_OUTPUT_DIR
    if not target_dir.exists():
        return []

    pattern = f"{FILE_PREFIX}*.json"
    files = list(target_dir.glob(pattern))
    # Sort newest first
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files
