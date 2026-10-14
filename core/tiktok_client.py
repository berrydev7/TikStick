"""TikTok HTTP Client for resolving URLs and retrieving comment streams."""

import time
from typing import Any, Dict, Generator, Optional, Tuple
import requests

from config import (
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    TIKTOK_COMMENT_LIST_URL,
    TIKTOK_COMMENT_REPLY_URL,
)
from core.comment_parser import CommentBatch, parse_comment_response
from utils.validators import (
    is_short_tiktok_url,
    validate_and_extract_video_id,
    sanitize_error_message,
)


class TikTokError(Exception):
    """Base error for TikTok client operations."""
    pass


class TikTokURLInvalidError(TikTokError):
    """Raised when the TikTok URL or video ID is invalid."""
    pass


class TikTokNetworkError(TikTokError):
    """Raised on connection timeout or network failures."""
    pass


class TikTokAPIError(TikTokError):
    """Raised when the TikTok API returns an error or blocked response."""
    pass


class TikTokClient:
    """Client for interacting with TikTok web endpoints."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: float = DEFAULT_TIMEOUT):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = timeout

    def resolve_video(self, url_or_id: str) -> Tuple[str, str]:
        """Resolve a video input into (canonical_url, video_id).

        Handles shortlinks (vt.tiktok.com, vm.tiktok.com, /t/) by following HTTP redirects.
        """
        if not url_or_id or not isinstance(url_or_id, str):
            raise TikTokURLInvalidError("TikTok video URL or ID cannot be empty.")

        raw_input = url_or_id.strip()

        # Check if already a pure numerical video ID
        direct_id = validate_and_extract_video_id(raw_input)
        if direct_id and raw_input == direct_id:
            return f"https://www.tiktok.com/video/{direct_id}", direct_id

        # Check if it's a short URL needing redirect resolution
        if is_short_tiktok_url(raw_input):
            try:
                # Follow redirects to get canonical URL
                resp = self.session.head(
                    raw_input,
                    allow_redirects=True,
                    timeout=self.timeout,
                )
                final_url = resp.url
            except Exception as e:
                # Try GET if HEAD fails
                try:
                    resp = self.session.get(
                        raw_input,
                        allow_redirects=True,
                        timeout=self.timeout,
                    )
                    final_url = resp.url
                except Exception as ex:
                    raise TikTokNetworkError(
                        f"Failed to resolve short URL: {sanitize_error_message(ex)}"
                    ) from ex

            resolved_id = validate_and_extract_video_id(final_url)
            if not resolved_id:
                raise TikTokURLInvalidError(f"Could not extract video ID from resolved URL: {final_url}")
            return final_url, resolved_id

        # Standard URL parsing
        video_id = validate_and_extract_video_id(raw_input)
        if not video_id:
            raise TikTokURLInvalidError(
                f"Invalid TikTok video URL or ID format: '{raw_input}'"
            )

        return raw_input, video_id

    def fetch_comment_page(
        self,
        video_id: str,
        cursor: int = 0,
        count: int = 50,
    ) -> CommentBatch:
        """Fetch a single page of top-level comments for a video."""
        params = {
            "aweme_id": video_id,
            "cursor": str(cursor),
            "count": str(count),
            "aid": "1988",
            "app_language": "en",
            "current_region": "US",
        }

        try:
            response = self.session.get(
                TIKTOK_COMMENT_LIST_URL,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise TikTokNetworkError(
                f"Network error while fetching comments: {sanitize_error_message(e)}"
            ) from e

        if response.status_code != 200:
            raise TikTokAPIError(
                f"TikTok API returned HTTP status {response.status_code}"
            )

        try:
            data = response.json()
        except Exception as e:
            raise TikTokAPIError("Failed to decode JSON response from TikTok") from e

        return parse_comment_response(data)

    def fetch_replies_page(
        self,
        video_id: str,
        comment_id: str,
        cursor: int = 0,
        count: int = 20,
    ) -> CommentBatch:
        """Fetch reply comments for a specific parent comment."""
        params = {
            "item_id": video_id,
            "comment_id": comment_id,
            "cursor": str(cursor),
            "count": str(count),
            "aid": "1988",
        }

        try:
            response = self.session.get(
                TIKTOK_COMMENT_REPLY_URL,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                return CommentBatch(comments=[], cursor=cursor, has_more=False)
            data = response.json()
            return parse_comment_response(data)
        except Exception:
            # Gracefully treat reply errors as end of replies
            return CommentBatch(comments=[], cursor=cursor, has_more=False)

    def iterate_comments(
        self,
        video_id: str,
        max_comments: Optional[int] = None,
        fetch_replies: bool = True,
        delay_seconds: float = 0.5,
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator yielding comments one by one, handling pagination and optional replies.

        Raises TikTokError on network or API issues so caller can capture partial data.
        """
        cursor = 0
        has_more = True
        total_yielded = 0

        while has_more:
            batch = self.fetch_comment_page(video_id=video_id, cursor=cursor, count=50)

            if not batch.comments:
                break

            for comment in batch.comments:
                yield comment
                total_yielded += 1

                if max_comments and total_yielded >= max_comments:
                    return

                # If this comment has replies and fetch_replies is enabled
                reply_total = comment.get("reply_comment_total", 0)
                cid = comment.get("cid")
                if fetch_replies and reply_total > 0 and cid:
                    reply_cursor = 0
                    reply_has_more = True
                    while reply_has_more:
                        reply_batch = self.fetch_replies_page(
                            video_id=video_id,
                            comment_id=cid,
                            cursor=reply_cursor,
                            count=20,
                        )
                        for r_comment in reply_batch.comments:
                            yield r_comment
                            total_yielded += 1
                            if max_comments and total_yielded >= max_comments:
                                return

                        reply_has_more = reply_batch.has_more and len(reply_batch.comments) > 0
                        reply_cursor = reply_batch.cursor
                        if reply_has_more:
                            time.sleep(0.2)

            has_more = batch.has_more
            cursor = batch.cursor

            if has_more:
                time.sleep(delay_seconds)
