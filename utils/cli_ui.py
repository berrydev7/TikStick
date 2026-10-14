"""Rich CLI user interface components for BERRY TikTok Sticker Scraper."""

from typing import List, Dict, Any, Optional
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

from config import APP_NAME, APP_VERSION
from utils.logger import get_console


def display_header() -> None:
    """Display the official Berry branding header panel."""
    console = get_console()
    title_text = f"[bold cyan]{APP_NAME.upper()}[/bold cyan]\n[dim]Version {APP_VERSION}[/dim]"
    panel = Panel(
        title_text,
        box=ROUNDED,
        border_style="cyan",
        expand=False,
        padding=(0, 4),
    )
    console.print()
    console.print(panel)
    console.print()


def display_menu_options() -> None:
    """Print the numbered menu options matching the requested style."""
    console = get_console()
    console.print("[cyan][1][/cyan] Scrape stickers from TikTok video")
    console.print("[cyan][2][/cyan] Extract sticker URLs from JSON")
    console.print("[cyan][3][/cyan] Download stickers from JSON")
    console.print("[cyan][4][/cyan] View previous results")
    console.print("[cyan][5][/cyan] Exit")


def prompt_menu_choice() -> str:
    """Prompt the user for a menu choice using questionary or rich input fallback."""
    try:
        import questionary
        from questionary import Style

        custom_style = Style(
            [
                ("qmark", "fg:#00ffff bold"),
                ("question", "bold"),
                ("answer", "fg:#00ff00 bold"),
                ("pointer", "fg:#00ffff bold"),
                ("highlighted", "fg:#00ffff bold"),
                ("selected", "fg:#00ff00"),
            ]
        )

        choices = [
            "[1] Scrape stickers from TikTok video",
            "[2] Extract sticker URLs from JSON",
            "[3] Download stickers from JSON",
            "[4] View previous results",
            "[5] Exit",
        ]

        result = questionary.select(
            "Select an option:",
            choices=choices,
            style=custom_style,
        ).ask()

        if result is None:
            return "5"

        # Extract digit [1] -> "1"
        for i in ("1", "2", "3", "4", "5"):
            if result.startswith(f"[{i}]"):
                return i
        return "5"

    except Exception:
        # Fallback for environments without interactive TTY support
        console = get_console()
        console.print()
        display_menu_options()
        try:
            choice = input("\nSelect an option (1-5): ").strip()
            return choice
        except (KeyboardInterrupt, EOFError):
            return "5"


def prompt_text(label: str, default: str = "") -> str:
    """Prompt the user for text input."""
    try:
        import questionary
        val = questionary.text(label, default=default).ask()
        if val is None:
            return ""
        return val.strip()
    except Exception:
        console = get_console()
        console.print(f"[cyan]{label}[/cyan]")
        try:
            return input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            return ""


def display_scraping_summary(
    video_id: str,
    comments_processed: int,
    stickers_found: int,
    unique_stickers: int,
    direct_urls_found: int,
    json_path: Path,
) -> None:
    """Display the final scraping summary panel matching the required design."""
    console = get_console()

    content = (
        f"[cyan]Video ID[/cyan]           : {video_id or 'N/A'}\n"
        f"[cyan]Comments processed[/cyan] : {comments_processed}\n"
        f"[cyan]Stickers found[/cyan]     : {stickers_found}\n"
        f"[cyan]Unique stickers[/cyan]    : {unique_stickers}\n"
        f"[cyan]Direct URLs found[/cyan]  : {direct_urls_found}\n"
        f"[cyan]JSON export[/cyan]        : {json_path.name}"
    )

    panel = Panel(
        content,
        title="[bold cyan]SCRAPING SUMMARY[/bold cyan]",
        box=ROUNDED,
        border_style="cyan",
        expand=False,
        padding=(0, 2),
    )
    console.print()
    console.print(panel)


def display_stickers_table(stickers: List[Dict[str, Any]], title: str = "EXTRACTED STICKERS") -> None:
    """Display a clean table of extracted stickers."""
    console = get_console()
    table = Table(
        title=f"[bold cyan]{title}[/bold cyan]",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="dim white",
    )

    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Sticker ID", style="cyan", width=18)
    table.add_column("Type", width=12)
    table.add_column("Status", width=12)
    table.add_column("Sticker URL", style="white")

    for idx, s in enumerate(stickers, 1):
        s_id = str(s.get("sticker_id") or "null")
        m_type = str(s.get("media_type") or "unknown")
        status = str(s.get("download_status") or "pending")
        url = str(s.get("sticker_url") or "null")

        status_style = "green" if status == "downloaded" else ("yellow" if status == "pending" else "red")
        table.add_row(
            str(idx),
            s_id,
            m_type,
            f"[{status_style}]{status}[/{status_style}]",
            url,
        )

    console.print()
    console.print(table)
    console.print(f"[dim]Total items: {len(stickers)}[/dim]")


def display_previous_results_table(files: List[Path]) -> None:
    """Display previous JSON exports found in the script directory."""
    console = get_console()
    if not files:
        console.print("[yellow]No previous JSON scraping results found in script directory.[/yellow]")
        return

    table = Table(
        title="[bold cyan]PREVIOUS SCRAPING RESULTS[/bold cyan]",
        box=ROUNDED,
        header_style="bold cyan",
        border_style="dim white",
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Filename", style="cyan")
    table.add_column("Size", justify="right", width=10)
    table.add_column("Last Modified", width=22)

    import datetime
    for idx, file in enumerate(files, 1):
        try:
            stat = file.stat()
            size_kb = f"{stat.st_size / 1024:.1f} KB"
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            size_kb = "N/A"
            mtime = "N/A"

        table.add_row(str(idx), file.name, size_kb, mtime)

    console.print()
    console.print(table)


def create_download_progress() -> Progress:
    """Create a progress bar for downloading sticker files."""
    console = get_console()
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=30, style="dim cyan", complete_style="bold cyan"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )
