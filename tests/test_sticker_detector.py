"""Unit tests for sticker detection and media type determination."""

import pytest
from core.sticker_detector import (
    determine_media_type,
    extract_stickers_from_comment,
)


def test_determine_media_type():
    assert determine_media_type("https://example.com/asset.webp") == "image/webp"
    assert determine_media_type("https://example.com/asset.gif") == "image/gif"
    assert determine_media_type("https://example.com/asset.png") == "image/png"
    assert determine_media_type("https://example.com/asset.jpg") == "image/jpeg"
    assert determine_media_type("https://example.com/asset.jpeg") == "image/jpeg"
    assert determine_media_type("https://example.com/asset.webp~tplv-tiktok-shrink:100:100.webp") == "image/webp"
    # Fallback default
    assert determine_media_type("https://example.com/unknown_extension") == "image/webp"


def test_extract_sticker_from_single_sticker_field():
    comment = {
        "cid": "7354928192305810721",
        "text": "Great sticker!",
        "sticker": {
            "id": "99887766",
            "url": {
                "url_list": [
                    "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1.webp"
                ]
            },
            "animate_url": {
                "url_list": [
                    "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_anim.webp"
                ]
            },
            "static_url": {
                "url_list": [
                    "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_thumb.webp"
                ]
            },
        },
    }

    stickers = extract_stickers_from_comment(comment)
    assert len(stickers) == 1
    s = stickers[0]

    assert s["comment_id"] == "7354928192305810721"
    assert s["sticker_id"] == "99887766"
    assert s["sticker_url"] == "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_anim.webp"
    assert s["thumbnail_url"] == "https://p16-sign-va.tiktokcdn.com/tos-maliva-i-0000/sticker1_thumb.webp"
    assert s["media_type"] == "image/webp"
    assert s["download_status"] == "pending"


def test_extract_sticker_with_missing_thumbnail():
    comment = {
        "cid": "comment_999",
        "sticker": {
            "id": "112233",
            "url": "https://example.com/simple_sticker.gif",
        },
    }

    stickers = extract_stickers_from_comment(comment)
    assert len(stickers) == 1
    s = stickers[0]
    assert s["sticker_id"] == "112233"
    assert s["sticker_url"] == "https://example.com/simple_sticker.gif"
    assert s["thumbnail_url"] is None
    assert s["media_type"] == "image/gif"


def test_extract_stickers_from_plural_field():
    comment = {
        "cid": "comment_multi",
        "stickers": [
            {
                "id": "s1",
                "url": {"url_list": ["https://example.com/s1.webp"]},
            },
            {
                "id": "s2",
                "url": {"url_list": ["https://example.com/s2.webp"]},
            },
        ],
    }

    stickers = extract_stickers_from_comment(comment)
    assert len(stickers) == 2
    assert stickers[0]["sticker_id"] == "s1"
    assert stickers[1]["sticker_id"] == "s2"


def test_extract_stickers_from_image_list():
    comment = {
        "cid": "comment_img",
        "image_list": [
            {
                "id": "img_001",
                "image_url": {
                    "url_list": ["https://example.com/attached_image.png"]
                },
            }
        ],
    }

    stickers = extract_stickers_from_comment(comment)
    assert len(stickers) == 1
    assert stickers[0]["sticker_id"] == "img_001"
    assert stickers[0]["sticker_url"] == "https://example.com/attached_image.png"
    assert stickers[0]["media_type"] == "image/png"


def test_comment_without_stickers():
    comment = {
        "cid": "comment_plain",
        "text": "Just a normal comment without any media attachments.",
        "reply_comment_total": 0,
    }
    stickers = extract_stickers_from_comment(comment)
    assert stickers == []


def test_no_fabricated_id_or_empty_url():
    # Sticker object with no id and empty url container
    comment = {
        "cid": "comment_empty",
        "sticker": {
            "url": {"url_list": ["", "   "]},
        },
    }
    stickers = extract_stickers_from_comment(comment)
    assert stickers == []


def test_extract_stickers_from_cmt_sticker_struct():
    """Verify modern TikTok cmt_sticker_struct is correctly detected."""
    comment = {
        "cid": "7689421199651668743",
        "text": "",
        "cmt_sticker_struct": {
            "id": "82771737633539",
            "animated_url": {
                "high_resolution_url": {
                    "url_list": [
                        "https://p16-tiktok-dm-sticker-sign-sg.ibyteimg.com/tos-alisg-i-dhq7zx4c1p-sg/5bc.awebp?rk3s=00edd399"
                    ]
                }
            },
            "static_url": {
                "high_resolution_url": {
                    "url_list": [
                        "https://p16-tiktok-dm-sticker-sign-sg.ibyteimg.com/tos-alisg-i-dhq7zx4c1p-sg/thumb.awebp?rk3s=00edd399"
                    ]
                }
            },
        },
    }

    stickers = extract_stickers_from_comment(comment)
    assert len(stickers) == 1
    s = stickers[0]
    assert s["comment_id"] == "7689421199651668743"
    assert s["sticker_id"] == "82771737633539"
    assert s["sticker_url"] == "https://p16-tiktok-dm-sticker-sign-sg.ibyteimg.com/tos-alisg-i-dhq7zx4c1p-sg/5bc.awebp?rk3s=00edd399"
    assert s["thumbnail_url"] == "https://p16-tiktok-dm-sticker-sign-sg.ibyteimg.com/tos-alisg-i-dhq7zx4c1p-sg/thumb.awebp?rk3s=00edd399"
    assert s["media_type"] == "image/webp"
    assert s["download_status"] == "pending"

