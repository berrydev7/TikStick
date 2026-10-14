"""Validation and sanitization utilities."""

import re
from typing import Optional, Union
from urllib.parse import urlparse


def validate_and_extract_video_id(url_or_id: str) -> Optional[str]:
    """Validate input string and extract TikTok video ID.

    Supports:
    - Pure numeric ID: '1234567890123456789'
    - Web URL: 'https://www.tiktok.com/@username/video/1234567890123456789'
    - Photo URL: 'https://www.tiktok.com/@username/photo/1234567890123456789'
    - Short/alt URL: 'https://www.tiktok.com/v/1234567890123456789'
    - Mobile URL: 'https://m.tiktok.com/v/1234567890123456789.html'
    - Shortlinks like vt.tiktok.com or vm.tiktok.com (returns None if not yet resolved to canonical ID)

    Returns:
        Video ID string if found and valid, otherwise None.
    """
    if not url_or_id or not isinstance(url_or_id, str):
        return None

    cleaned = url_or_id.strip()

    # Direct numerical video ID (TikTok IDs are typically 15 to 22 digits)
    if re.fullmatch(r"\d{15,22}", cleaned):
        return cleaned

    # Standard video/photo pattern
    match = re.search(r"/(?:video|photo|v)/(\d{15,22})", cleaned)
    if match:
        return match.group(1)

    # Alternate pattern for URLs ending with numeric ID before query string or slash
    alt_match = re.search(r"[/?&]aweme_id=(\d{15,22})", cleaned)
    if alt_match:
        return alt_match.group(1)

    return None


def is_short_tiktok_url(url: str) -> bool:
    """Check if the URL is a TikTok short link that needs resolution."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    domain = parsed.netloc.lower()
    return any(s in domain for s in ("vt.tiktok.com", "vm.tiktok.com")) or (
        "tiktok.com" in domain and parsed.path.startswith("/t/")
    )


def is_valid_http_url(url: Optional[str]) -> bool:
    """Validate whether a string is a non-empty, well-formed HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False

    trimmed = url.strip()
    if not trimmed:
        return False

    try:
        result = urlparse(trimmed)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def sanitize_error_message(err: Union[Exception, str]) -> str:
    """Sanitize error messages to prevent leaking sensitive tokens or credentials."""
    msg = str(err)

    # Patterns for sensitive TikTok parameters and cookies
    sensitive_keys = [
        "sessionid",
        "msToken",
        "X-Bogus",
        "_signature",
        "tt_csrf_token",
        "tt_chain_token",
        "passport_csrf_token",
        "access_token",
        "bearer",
        "password",
        "secret",
        "cookie",
    ]

    for key in sensitive_keys:
        # Mask query params or key-values: key=VALUE
        msg = re.sub(
            rf"({key}\s*=\s*)([^\s&;,'\"]+)",
            r"\1[REDACTED]",
            msg,
            flags=re.IGNORECASE,
        )

    return msg


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters for filesystem filenames."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)
