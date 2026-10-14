"""Unit tests for JSON exporter, default directory persistence, and error handling."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config import APP_NAME, APP_VERSION, SCRIPT_DIR
from core.exporter import (
    build_output_payload,
    generate_output_filename,
    load_json_file,
    resolve_non_colliding_path,
    write_json_file,
)
from core.tiktok_client import TikTokAPIError, TikTokClient, TikTokURLInvalidError
from main import run_scraper


def test_default_output_dir_matches_script_dir():
    from config import DEFAULT_OUTPUT_DIR
    assert DEFAULT_OUTPUT_DIR == SCRIPT_DIR
    assert SCRIPT_DIR.is_dir()


def test_output_independent_of_cwd(tmp_path, monkeypatch):
    """Ensure that changing the working directory does NOT alter the default output location."""
    fake_cwd = tmp_path / "somewhere_else"
    fake_cwd.mkdir()

    # Change current working directory to temporary folder
    monkeypatch.chdir(fake_cwd)
    assert Path.cwd() == fake_cwd

    # Mock TikTok client to avoid real network call
    mock_client = MagicMock(spec=TikTokClient)
    mock_client.resolve_video.return_value = (
        "https://www.tiktok.com/@user/video/7354928192305810721",
        "7354928192305810721",
    )
    mock_client.iterate_comments.return_value = iter([])

    # Run scraper without --output argument
    saved_file, payload = run_scraper(
        video_url_or_id="7354928192305810721",
        output_path=None,
        client=mock_client,
    )

    try:
        # File must be in SCRIPT_DIR, NOT in fake_cwd
        assert saved_file.parent == SCRIPT_DIR
        assert not (fake_cwd / saved_file.name).exists()
        assert saved_file.exists()
    finally:
        # Cleanup created test file in SCRIPT_DIR
        if saved_file.exists():
            saved_file.unlink()


def test_json_readable_back(tmp_path):
    """Verify saved JSON is strictly valid, readable with json.load, and has correct schema."""
    target_file = tmp_path / "berry_stickers_test.json"
    dt = datetime.now().astimezone()

    sample_stickers = [
        {
            "comment_id": "c1",
            "sticker_id": "s1",
            "sticker_url": "https://example.com/s1.webp",
            "thumbnail_url": None,
            "media_type": "image/webp",
            "download_status": "pending",
        }
    ]

    payload = build_output_payload(
        video_url="https://www.tiktok.com/@u/video/123",
        video_id="123",
        started_at=dt,
        completed_at=dt,
        comments_processed=10,
        stickers=sample_stickers,
        errors=[],
        status="completed",
    )

    write_json_file(payload, target_file)
    assert target_file.exists()

    # Read back using json.load
    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["tool"] == APP_NAME
    assert loaded["version"] == APP_VERSION
    assert loaded["source"]["video_id"] == "123"
    assert loaded["scraping"]["comments_processed"] == 10
    assert loaded["scraping"]["stickers_found"] == 1
    assert loaded["scraping"]["unique_stickers"] == 1
    assert loaded["scraping"]["direct_urls_found"] == 1
    assert loaded["scraping"]["status"] == "completed"
    assert len(loaded["stickers"]) == 1
    assert loaded["errors"] == []

    # Also test load_json_file helper
    helper_loaded = load_json_file(target_file)
    assert helper_loaded == loaded


def test_old_files_not_overwritten_collision_handled(tmp_path):
    """Test that existing files are never overwritten and numeric suffixes are appended."""
    base_name = "berry_stickers_20261014_083000.json"
    file1 = tmp_path / base_name
    file1.write_text('{"initial": 1}', encoding="utf-8")

    # First collision should become _1
    p2 = resolve_non_colliding_path(tmp_path, base_name)
    assert p2.name == "berry_stickers_20261014_083000_1.json"
    p2.write_text('{"second": 2}', encoding="utf-8")

    # Second collision should become _2
    p3 = resolve_non_colliding_path(tmp_path, base_name)
    assert p3.name == "berry_stickers_20261014_083000_2.json"

    # Original file is preserved
    assert file1.read_text(encoding="utf-8") == '{"initial": 1}'


def test_partial_data_saved_on_interruption(tmp_path):
    """Verify that if an error occurs mid-scraping, partial results and errors are safely saved."""
    mock_client = MagicMock(spec=TikTokClient)
    mock_client.resolve_video.return_value = (
        "https://www.tiktok.com/@u/video/7354928192305810721",
        "7354928192305810721",
    )

    def fake_comment_generator(video_id, max_comments=None):
        # First comment with sticker
        yield {
            "cid": "c1",
            "sticker": {
                "id": "stk_1",
                "url": {"url_list": ["https://example.com/stk1.webp"]},
            },
        }
        # Second comment without sticker
        yield {
            "cid": "c2",
            "text": "Hello",
        }
        # Third comment raises rate limit error
        raise TikTokAPIError("TikTok rate limit exceeded")

    mock_client.iterate_comments.side_effect = fake_comment_generator

    custom_out = tmp_path / "partial_test.json"
    saved_file, payload = run_scraper(
        video_url_or_id="7354928192305810721",
        output_path=custom_out,
        client=mock_client,
    )

    assert saved_file.exists()
    assert payload["scraping"]["status"] == "partial"
    assert payload["scraping"]["comments_processed"] == 2
    assert payload["scraping"]["stickers_found"] == 1
    assert payload["scraping"]["unique_stickers"] == 1
    assert len(payload["stickers"]) == 1
    assert any("rate limit" in err for err in payload["errors"])


def test_failed_data_saved_on_early_error(tmp_path):
    """Verify that failure before gathering data saves valid JSON with status 'failed'."""
    mock_client = MagicMock(spec=TikTokClient)
    mock_client.resolve_video.side_effect = TikTokURLInvalidError("Invalid video URL format")

    custom_out = tmp_path / "failed_test.json"
    saved_file, payload = run_scraper(
        video_url_or_id="invalid_input",
        output_path=custom_out,
        client=mock_client,
    )

    assert saved_file.exists()
    assert payload["scraping"]["status"] == "failed"
    assert payload["scraping"]["comments_processed"] == 0
    assert payload["scraping"]["stickers_found"] == 0
    assert len(payload["errors"]) == 1
    assert "Invalid video URL" in payload["errors"][0]


def test_custom_output_argument(tmp_path):
    """Verify that --output saves explicitly to the user's custom location."""
    mock_client = MagicMock(spec=TikTokClient)
    mock_client.resolve_video.return_value = ("https://tiktok.com/v/123", "123")
    mock_client.iterate_comments.return_value = iter([])

    custom_dir = tmp_path / "my_custom_folder"
    custom_dir.mkdir()
    custom_file = custom_dir / "user_specified_result.json"

    saved_file, payload = run_scraper(
        video_url_or_id="123",
        output_path=custom_file,
        client=mock_client,
    )

    assert saved_file == custom_file.resolve()
    assert saved_file.exists()


def test_summary_counts_match_actual_data():
    """Verify metrics calculation logic strictly reflects payload items."""
    dt = datetime.now(timezone.utc)
    stickers = [
        {"comment_id": "1", "sticker_id": "A", "sticker_url": "https://example.com/a.webp"},
        {"comment_id": "2", "sticker_id": "A", "sticker_url": "https://example.com/a.webp"},  # duplicate id
        {"comment_id": "3", "sticker_id": "B", "sticker_url": "https://example.com/b.webp"},
        {"comment_id": "4", "sticker_id": None, "sticker_url": ""},  # empty url
    ]

    payload = build_output_payload(
        video_url="https://tiktok.com/v/123",
        video_id="123",
        started_at=dt,
        completed_at=dt,
        comments_processed=50,
        stickers=stickers,
        errors=[],
        status="completed",
    )

    s_meta = payload["scraping"]
    assert s_meta["comments_processed"] == 50
    assert s_meta["stickers_found"] == 4
    # Unique keys: 'A', 'B' -> 2
    assert s_meta["unique_stickers"] == 2
    # Direct URLs: 'https://example.com/a.webp' (x2) + 'https://example.com/b.webp' -> 3
    assert s_meta["direct_urls_found"] == 3


def test_cli_displays_error_clearly_on_missing_file(capsys):
    """Verify CLI error handling outputs clear error when file is missing."""
    from main import handle_extract_json

    handle_extract_json("non_existent_file_berry_123.json")
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.out or "Failed to read JSON" in captured.out or "File not found" in captured.out


def test_sticker_downloader_workflow(tmp_path):
    """Verify downloader updates status and writes binary files."""
    from core.sticker_downloader import download_stickers_from_list

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.iter_content.return_value = [b"fake_image_bytes"]
    mock_session.get.return_value = mock_resp

    stickers = [
        {
            "comment_id": "c1",
            "sticker_id": "101",
            "sticker_url": "https://example.com/image.webp",
            "thumbnail_url": None,
            "media_type": "image/webp",
            "download_status": "pending",
        },
        {
            "comment_id": "c2",
            "sticker_id": "102",
            "sticker_url": None,
            "thumbnail_url": None,
            "media_type": "image/webp",
            "download_status": "pending",
        },
    ]

    target_dir = tmp_path / "downloaded_stickers"
    summary = download_stickers_from_list(
        stickers=stickers,
        output_dir=target_dir,
        session=mock_session,
        show_progress=False,
    )

    assert summary["downloaded"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 0
    assert stickers[0]["download_status"] == "downloaded"
    assert "local_path" in stickers[0]
    assert Path(stickers[0]["local_path"]).exists()

