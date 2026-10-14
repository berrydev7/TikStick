"""Comment parser for TikTok comment API responses."""

from typing import Any, Dict, List, Optional, Tuple


class CommentBatch:
    """Represents a parsed page/batch of comments from TikTok."""

    def __init__(
        self,
        comments: List[Dict[str, Any]],
        cursor: int,
        has_more: bool,
        total: Optional[int] = None,
    ):
        self.comments = comments
        self.cursor = cursor
        self.has_more = has_more
        self.total = total


def parse_comment_response(data: Dict[str, Any]) -> CommentBatch:
    """Parse raw JSON response from TikTok comment list API."""
    if not isinstance(data, dict):
        raise ValueError("Invalid comment response: Expected JSON dictionary")

    # TikTok status codes: 0 means OK
    status_code = data.get("status_code")
    if status_code is not None and status_code != 0:
        status_msg = data.get("status_msg") or f"TikTok API error code: {status_code}"
        raise RuntimeError(status_msg)

    # Extract comments list
    raw_comments = data.get("comments")
    if raw_comments is None:
        # Fallback check for nested data
        raw_comments = data.get("data", {}).get("comments", [])

    if not isinstance(raw_comments, list):
        raw_comments = []

    cursor = data.get("cursor", 0)
    try:
        cursor = int(cursor)
    except (ValueError, TypeError):
        cursor = 0

    has_more = bool(data.get("has_more", 0))
    total = data.get("total")
    if total is not None:
        try:
            total = int(total)
        except (ValueError, TypeError):
            total = None

    parsed_comments: List[Dict[str, Any]] = []

    for item in raw_comments:
        if not isinstance(item, dict):
            continue

        cid = str(item.get("cid") or item.get("id") or "")
        text = str(item.get("text") or "")
        create_time = item.get("create_time")

        user_info = item.get("user") or {}
        username = user_info.get("unique_id") or user_info.get("nickname") or "unknown"

        reply_count = item.get("reply_comment_total", 0)

        parsed_item = {
            "cid": cid,
            "text": text,
            "username": username,
            "create_time": create_time,
            "reply_comment_total": reply_count,
            "raw": item,
        }

        # Include any sticker or image data from the raw item
        if "sticker" in item:
            parsed_item["sticker"] = item["sticker"]
        if "stickers" in item:
            parsed_item["stickers"] = item["stickers"]
        if "image_list" in item:
            parsed_item["image_list"] = item["image_list"]

        parsed_comments.append(parsed_item)

        # Include reply comments if embedded in the item
        reply_list = item.get("reply_comment")
        if isinstance(reply_list, list):
            for reply in reply_list:
                if isinstance(reply, dict):
                    r_cid = str(reply.get("cid") or reply.get("id") or "")
                    r_parsed = {
                        "cid": r_cid,
                        "text": str(reply.get("text") or ""),
                        "username": (reply.get("user") or {}).get("unique_id", "unknown"),
                        "create_time": reply.get("create_time"),
                        "reply_comment_total": 0,
                        "raw": reply,
                    }
                    if "sticker" in reply:
                        r_parsed["sticker"] = reply["sticker"]
                    if "stickers" in reply:
                        r_parsed["stickers"] = reply["stickers"]
                    if "image_list" in reply:
                        r_parsed["image_list"] = reply["image_list"]

                    parsed_comments.append(r_parsed)

    return CommentBatch(
        comments=parsed_comments,
        cursor=cursor,
        has_more=has_more,
        total=total,
    )
