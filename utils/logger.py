"""Terminal logger with consistent color branding for BERRY."""

import sys
from typing import Optional
from rich.console import Console
from rich.theme import Theme

# Berry color theme:
# Cyan: Information
# Green: Success
# Yellow: Warning
# Red: Error
# White/Grey: Plain text
BERRY_THEME = Theme(
    {
        "info": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "highlight": "cyan",
        "muted": "dim white",
    }
)

_GLOBAL_CONSOLE: Optional[Console] = None
_NO_COLOR_SETTING = False


def init_console(no_color: bool = False) -> Console:
    """Initialize or update the global console."""
    global _GLOBAL_CONSOLE, _NO_COLOR_SETTING
    _NO_COLOR_SETTING = no_color
    _GLOBAL_CONSOLE = Console(
        theme=BERRY_THEME,
        no_color=no_color,
        color_system=None if no_color else "auto",
        highlight=False,
    )
    return _GLOBAL_CONSOLE


def get_console() -> Console:
    """Get the current rich console instance."""
    global _GLOBAL_CONSOLE
    if _GLOBAL_CONSOLE is None:
        _GLOBAL_CONSOLE = init_console()
    return _GLOBAL_CONSOLE


def set_no_color(no_color: bool) -> None:
    """Toggle color output on or off."""
    init_console(no_color=no_color)


class BerryLogger:
    """Logger that prints formatted status messages to the terminal."""

    @staticmethod
    def info(message: str) -> None:
        console = get_console()
        console.print(f"[info][INFO][/info] {message}")

    @staticmethod
    def success(message: str) -> None:
        console = get_console()
        console.print(f"[success][+][/success] {message}")

    @staticmethod
    def warning(message: str) -> None:
        console = get_console()
        console.print(f"[warning][WARNING][/warning] {message}")

    @staticmethod
    def error(message: str) -> None:
        console = get_console()
        console.print(f"[error][ERROR][/error] {message}")

    @staticmethod
    def print(message: str = "") -> None:
        console = get_console()
        console.print(message)


logger = BerryLogger()
