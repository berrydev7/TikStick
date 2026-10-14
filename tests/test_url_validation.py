"""Unit tests for URL and video ID validation."""

import pytest
from utils.validators import (
    is_short_tiktok_url,
    is_valid_http_url,
    sanitize_error_message,
    validate_and_extract_video_id,
)


def test_extract_video_id_from_standard_url():
    url = "https://www.tiktok.com/@username/video/7354928192305810721"
    assert validate_and_extract_video_id(url) == "7354928192305810721"


def test_extract_video_id_with_query_parameters():
    url = "https://www.tiktok.com/@username/video/7354928192305810721?is_from_webapp=1&sender_device=pc"
    assert validate_and_extract_video_id(url) == "7354928192305810721"


def test_extract_video_id_from_photo_url():
    url = "https://www.tiktok.com/@username/photo/7354928192305810721"
    assert validate_and_extract_video_id(url) == "7354928192305810721"


def test_extract_video_id_from_v_url():
    url = "https://www.tiktok.com/v/7354928192305810721"
    assert validate_and_extract_video_id(url) == "7354928192305810721"


def test_extract_pure_numerical_id():
    video_id = "7354928192305810721"
    assert validate_and_extract_video_id(video_id) == "7354928192305810721"


def test_detect_short_urls():
    assert is_short_tiktok_url("https://vt.tiktok.com/ZSjR12345/")
    assert is_short_tiktok_url("https://vm.tiktok.com/ZM812345/")
    assert is_short_tiktok_url("https://www.tiktok.com/t/ZT8abc123/")
    assert not is_short_tiktok_url("https://www.tiktok.com/@user/video/7354928192305810721")


def test_reject_invalid_urls():
    assert validate_and_extract_video_id("") is None
    assert validate_and_extract_video_id("https://google.com") is None
    assert validate_and_extract_video_id("https://www.tiktok.com/@onlyuser") is None
    assert validate_and_extract_video_id("12345") is None  # Too short for TikTok ID


def test_is_valid_http_url():
    assert is_valid_http_url("https://example.com/sticker.webp")
    assert is_valid_http_url("http://example.com/sticker.png")
    assert not is_valid_http_url("")
    assert not is_valid_http_url(None)
    assert not is_valid_http_url("not_a_url")
    assert not is_valid_http_url("ftp://example.com/file")


def test_sanitize_error_message():
    err_msg = "Request failed at https://tiktok.com/api?msToken=SUPER_SECRET_123&sessionid=ABC_XYZ_999"
    sanitized = sanitize_error_message(err_msg)
    assert "SUPER_SECRET_123" not in sanitized
    assert "ABC_XYZ_999" not in sanitized
    assert "msToken=[REDACTED]" in sanitized
    assert "sessionid=[REDACTED]" in sanitized
