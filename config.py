"""Configuration settings for Berry TikTok Sticker Scraper."""

from pathlib import Path

APP_NAME = "Berry TikTok Sticker Scraper"
APP_VERSION = "1.0.0"
BRAND_TITLE = "BERRY TIKTOK STICKER SCRAPER"

# SCRIPT_DIR is the root directory where main.py resides.
# Output JSON must be saved here by default, NOT in the terminal's working directory.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR

FILE_PREFIX = "berry_stickers_"

# Network settings
DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Referer": "https://www.tiktok.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# TikTok endpoints
TIKTOK_BASE_URL = "https://www.tiktok.com"
TIKTOK_COMMENT_LIST_URL = "https://www.tiktok.com/api/comment/list/"
TIKTOK_COMMENT_REPLY_URL = "https://www.tiktok.com/api/comment/list/reply/"
