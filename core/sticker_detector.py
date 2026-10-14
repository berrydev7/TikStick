"""Sticker detection and extraction engine for TikTok comments."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from utils.validators import is_valid_http_url


def determine_media_type(url: Optional[str]) -> str:
    """Determine media MIME type based on file extension in URL path."""
    if not url:
        return "image/webp"

    try:
        path = urlparse(url).path.lower()
        if path.endswith(".gif") or ".gif~" in path or "~tplv-tiktok-shrink" in path and ".gif" in path:
            return "image/gif"
        if path.endswith(".png") or ".png~" in path:
            return "image/png"
        if path.endswith(".jpg") or path.endswith(".jpeg") or ".jpeg~" in path or ".jpg~" in path:
            return "image/jpeg"
        if path.endswith(".webp") or ".webp~" in path:
            return "image/webp"
    except Exception:
        pass

    return "image/webp"


def _extract_url_from_url_container(container: Any) -> Optional[str]:
    """Helper to safely extract the first valid HTTP/HTTPS URL from a TikTok URL container."""
    if not container:
        return None

    if isinstance(container, str):
        url = container.strip()
        return url if is_valid_http_url(url) else None

    if isinstance(container, list):
        for item in container:
            extracted = _extract_url_from_url_container(item)
            if extracted:
                return extracted
        return None

    if isinstance(container, dict):
        # TikTok often places URLs in 'url_list' or 'download_url_list' or 'uri'
        for key in ("url_list", "download_url_list", "image_url", "url"):
            val = container.get(key)
            if val:
                extracted = _extract_url_from_url_container(val)
                if extracted:
                    return extracted

    return None


def extract_stickers_from_comment(comment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Inspect a comment object and detect any sticker attachments.

    Returns a list of sticker dictionaries adhering to:
    {
        "comment_id": str,
        "sticker_id": Optional[str],
        "sticker_url": Optional[str],
        "thumbnail_url": Optional[str],
        "media_type": str,
        "download_status": "pending"
    }
    """
    if not isinstance(comment, dict):
        return []

    comment_id = str(comment.get("cid") or comment.get("id") or comment.get("comment_id") or "")
    if not comment_id:
        comment_id = "unknown"

    detected: List[Dict[str, Any]] = []

    # Check 1: Single sticker field: comment.get("sticker")
    sticker_obj = comment.get("sticker")
    if isinstance(sticker_obj, dict):
        stk = _parse_sticker_dict(sticker_obj, comment_id)
        if stk:
            detected.append(stk)

    # Check 2: Plural stickers field: comment.get("stickers")
    stickers_list = comment.get("stickers")
    if isinstance(stickers_list, list):
        for item in stickers_list:
            if isinstance(item, dict):
                stk = _parse_sticker_dict(item, comment_id)
                if stk:
                    detected.append(stk)

    # Check 3: Comment image_list attachment (often stickers or custom images in comments)
    images_list = comment.get("image_list")
    if isinstance(images_list, list):
        for img in images_list:
            if isinstance(img, dict):
                stk = _parse_image_attachment(img, comment_id)
                if stk:
                    detected.append(stk)

    # Check 4: Pre-extracted sticker payload (e.g., if input is already formatted)
    if "sticker_url" in comment and is_valid_http_url(comment.get("sticker_url")):
        s_id = str(comment.get("sticker_id")) if comment.get("sticker_id") is not None else None
        s_url = comment.get("sticker_url")
        detected.append(
            {
                "comment_id": comment_id,
                "sticker_id": s_id,
                "sticker_url": s_url,
                "thumbnail_url": comment.get("thumbnail_url") or None,
                "media_type": comment.get("media_type") or determine_media_type(s_url),
                "download_status": comment.get("download_status") or "pending",
            }
        )

    return detected


def _parse_sticker_dict(data: Dict[str, Any], comment_id: str) -> Optional[Dict[str, Any]]:
    """Extract sticker attributes from a TikTok sticker dictionary."""
    raw_id = data.get("id") or data.get("sticker_id")
    sticker_id = str(raw_id) if raw_id is not None and str(raw_id).strip() else None

    # Priority for sticker media URL:
    # 1. animate_url (full animated webp / gif)
    # 2. url (standard image/sticker)
    # 3. static_url (static fallback)
    sticker_url = (
        _extract_url_from_url_container(data.get("animate_url"))
        or _extract_url_from_url_container(data.get("url"))
        or _extract_url_from_url_container(data.get("static_url"))
    )

    # Thumbnail URL
    thumbnail_url = (
        _extract_url_from_url_container(data.get("static_url"))
        or _extract_url_from_url_container(data.get("thumbnail_url"))
        or None
    )

    # If both id and url are missing, it's not a valid sticker attachment
    if not sticker_id and not sticker_url:
        return None

    media_type = determine_media_type(sticker_url)

    return {
        "comment_id": comment_id,
        "sticker_id": sticker_id,
        "sticker_url": sticker_url,
        "thumbnail_url": thumbnail_url,
        "media_type": media_type,
        "download_status": "pending",
    }


def _parse_image_attachment(data: Dict[str, Any], comment_id: str) -> Optional[Dict[str, Any]]:
    """Parse image_list item that may contain sticker/image media."""
    raw_id = data.get("id") or data.get("image_id")
    sticker_id = str(raw_id) if raw_id is not None and str(raw_id).strip() else None

    sticker_url = (
        _extract_url_from_url_container(data.get("image_url"))
        or _extract_url_from_url_container(data.get("url"))
        or _extract_url_from_url_container(data.get("url_list"))
    )

    if not sticker_url and not sticker_id:
        return None

    media_type = determine_media_type(sticker_url)

    return {
        "comment_id": comment_id,
        "sticker_id": sticker_id,
        "sticker_url": sticker_url,
        "thumbnail_url": None,
        "media_type": media_type,
        "download_status": "pending",
    }
