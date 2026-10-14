"""Sticker detection and extraction engine for TikTok comments."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from utils.validators import is_valid_http_url


def determine_media_type(url: Optional[str]) -> str:
    """Determine media MIME type based on file extension or pattern in URL."""
    if not url:
        return "image/webp"

    try:
        path = urlparse(url).path.lower()
        if ".gif" in path:
            return "image/gif"
        if ".png" in path:
            return "image/png"
        if ".jpg" in path or ".jpeg" in path:
            return "image/jpeg"
        if ".webp" in path or ".awebp" in path:
            return "image/webp"
    except Exception:
        pass

    return "image/webp"


def _extract_all_urls(container: Any) -> List[str]:
    """Recursively extract all valid HTTP/HTTPS URLs from nested structures."""
    urls: List[str] = []
    if not container:
        return urls

    if isinstance(container, str):
        trimmed = container.strip()
        if is_valid_http_url(trimmed):
            urls.append(trimmed)
    elif isinstance(container, list):
        for item in container:
            urls.extend(_extract_all_urls(item))
    elif isinstance(container, dict):
        # Priority order for URL resolution
        priority_keys = (
            "high_resolution_url",
            "animated_url",
            "animate_url",
            "origin_url",
            "mid_resolution_url",
            "low_resolution_url",
            "static_url",
            "crop_url",
            "url_list",
            "download_url_list",
            "image_url",
            "url",
        )
        for key in priority_keys:
            if key in container:
                urls.extend(_extract_all_urls(container[key]))
        for key, val in container.items():
            if key not in priority_keys:
                urls.extend(_extract_all_urls(val))

    return urls


def _extract_url_from_url_container(container: Any) -> Optional[str]:
    """Extract the first valid HTTP/HTTPS URL from a TikTok URL container."""
    urls = _extract_all_urls(container)
    return urls[0] if urls else None


def extract_stickers_from_comment(comment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Inspect a comment object and detect any sticker attachments.

    Checks:
    - cmt_sticker_struct (TikTok's standard comment sticker structure)
    - sticker (legacy/single sticker field)
    - stickers (plural sticker list)
    - image_list (comment images and custom sticker attachments)
    - Raw nested dictionaries if wrapped
    """
    if not isinstance(comment, dict):
        return []

    comment_id = str(comment.get("cid") or comment.get("id") or comment.get("comment_id") or "")
    if not comment_id:
        comment_id = "unknown"

    detected: List[Dict[str, Any]] = []

    # Check 1: TikTok standard cmt_sticker_struct
    cmt_sticker = comment.get("cmt_sticker_struct")
    if not cmt_sticker and isinstance(comment.get("raw"), dict):
        cmt_sticker = comment["raw"].get("cmt_sticker_struct")

    if isinstance(cmt_sticker, dict):
        stk = _parse_cmt_sticker_struct(cmt_sticker, comment_id)
        if stk:
            detected.append(stk)

    # Check 2: Single sticker field: comment.get("sticker")
    sticker_obj = comment.get("sticker")
    if not sticker_obj and isinstance(comment.get("raw"), dict):
        sticker_obj = comment["raw"].get("sticker")

    if isinstance(sticker_obj, dict):
        stk = _parse_sticker_dict(sticker_obj, comment_id)
        if stk:
            detected.append(stk)

    # Check 3: Plural stickers field: comment.get("stickers")
    stickers_list = comment.get("stickers")
    if not stickers_list and isinstance(comment.get("raw"), dict):
        stickers_list = comment["raw"].get("stickers")

    if isinstance(stickers_list, list):
        for item in stickers_list:
            if isinstance(item, dict):
                stk = _parse_sticker_dict(item, comment_id)
                if stk:
                    detected.append(stk)

    # Check 4: Comment image_list attachment
    images_list = comment.get("image_list")
    if not images_list and isinstance(comment.get("raw"), dict):
        images_list = comment["raw"].get("image_list")

    if isinstance(images_list, list):
        for img in images_list:
            if isinstance(img, dict):
                stk = _parse_image_attachment(img, comment_id)
                if stk:
                    detected.append(stk)

    # Check 5: Pre-extracted sticker payload
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

    # Deduplicate within the same comment
    unique_detected: List[Dict[str, Any]] = []
    seen_keys = set()
    for item in detected:
        k = item.get("sticker_id") or item.get("sticker_url")
        if k and k not in seen_keys:
            seen_keys.add(k)
            unique_detected.append(item)
        elif not k:
            unique_detected.append(item)

    return unique_detected


def _parse_cmt_sticker_struct(data: Dict[str, Any], comment_id: str) -> Optional[Dict[str, Any]]:
    """Parse TikTok's cmt_sticker_struct object."""
    raw_id = data.get("id") or data.get("sticker_id")
    sticker_id = str(raw_id) if raw_id is not None and str(raw_id).strip() else None

    # Animated URL (preferred for stickers)
    anim_urls = _extract_all_urls(data.get("animated_url") or data.get("animate_url"))
    # Static URL (thumbnail)
    static_urls = _extract_all_urls(data.get("static_url"))
    # Fallback all URLs
    all_urls = _extract_all_urls(data)

    sticker_url = anim_urls[0] if anim_urls else (all_urls[0] if all_urls else None)
    thumbnail_url = static_urls[0] if static_urls else None

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


def _parse_sticker_dict(data: Dict[str, Any], comment_id: str) -> Optional[Dict[str, Any]]:
    """Extract sticker attributes from a standard or legacy sticker dictionary."""
    raw_id = data.get("id") or data.get("sticker_id")
    sticker_id = str(raw_id) if raw_id is not None and str(raw_id).strip() else None

    # Priority for sticker media URL:
    # 1. animate_url / animated_url (animated webp / gif)
    # 2. url (standard image/sticker)
    # 3. static_url (static fallback)
    anim_urls = _extract_all_urls(data.get("animate_url") or data.get("animated_url"))
    std_urls = _extract_all_urls(data.get("url"))
    static_urls = _extract_all_urls(data.get("static_url"))
    all_urls = _extract_all_urls(data)

    sticker_url = (
        anim_urls[0]
        if anim_urls
        else (std_urls[0] if std_urls else (static_urls[0] if static_urls else (all_urls[0] if all_urls else None)))
    )

    thumbnail_url = (
        static_urls[0]
        if static_urls
        else (_extract_url_from_url_container(data.get("thumbnail_url")) or None)
    )

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
    """Parse image_list item that contains sticker or image media."""
    raw_id = data.get("id") or data.get("image_id")
    sticker_id = str(raw_id) if raw_id is not None and str(raw_id).strip() else None

    urls = (
        _extract_all_urls(data.get("origin_url"))
        or _extract_all_urls(data.get("image_url"))
        or _extract_all_urls(data.get("crop_url"))
        or _extract_all_urls(data.get("url"))
        or _extract_all_urls(data)
    )

    sticker_url = urls[0] if urls else None

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
