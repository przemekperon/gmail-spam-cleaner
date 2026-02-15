"""Rich-based display functions for Gmail Spam Cleaner."""

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt
from rich.table import Table

from .models import ScanResult, SenderProfile
from .scorer import classify_sender

console = Console()


def _score_color(score: float) -> str:
    """Return a Rich color name based on the score value."""
    if score >= 0.7:
        return "red"
    if score >= 0.5:
        return "yellow"
    if score < 0.3:
        return "green"
    return "white"


def display_scan_results(scan_result: ScanResult, min_score: float = 0.0) -> None:
    """Display scan results sorted by message count descending, excluding personal senders."""
    from .constants import SCORE_UNCERTAIN

    profiles = [
        p for p in scan_result.senders.values()
        if p.score >= max(min_score, SCORE_UNCERTAIN)
    ]
    # Sort by classification group (newsletter first, then likely, then uncertain),
    # then by message count within each group
    _CLASS_ORDER = {"newsletter": 0, "likely_newsletter": 1, "uncertain": 2}
    profiles.sort(key=lambda p: (_CLASS_ORDER.get(classify_sender(p.score), 3), -p.message_count))

    table = Table(title="Scan Results")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Email")
    table.add_column("Name")
    table.add_column("Count", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Classification")

    total_messages = 0
    for idx, profile in enumerate(profiles, start=1):
        color = _score_color(profile.score)
        classification = classify_sender(profile.score)
        total_messages += profile.message_count
        table.add_row(
            str(idx),
            f"[{color}]{profile.email}[/{color}]",
            profile.name,
            str(profile.message_count),
            f"[{color}]{profile.score:.2f}[/{color}]",
            f"[{color}]{classification}[/{color}]",
        )

    console.print(table)
    console.print(
        Panel(
            f"Total senders shown: {len(profiles)}  |  "
            f"Total messages: {total_messages}",
            title="Summary",
        )
    )


def create_progress(description: str) -> Progress:
    """Create a configured Rich Progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]{description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def display_sender_detail(profile: SenderProfile) -> None:
    """Display detailed information for a single sender."""
    classification = classify_sender(profile.score)
    color = _score_color(profile.score)

    lines = [
        f"[bold]Email:[/bold] {profile.email}",
        f"[bold]Name:[/bold] {profile.name}",
        f"[bold]Messages:[/bold] {profile.message_count}",
        f"[bold]Score:[/bold] [{color}]{profile.score:.2f}[/{color}]",
        f"[bold]Classification:[/bold] [{color}]{classification}[/{color}]",
    ]

    if profile.sample_subjects:
        lines.append("")
        lines.append("[bold]Sample subjects:[/bold]")
        for subject in profile.sample_subjects:
            lines.append(f"  - {subject}")

    console.print(Panel("\n".join(lines), title="Sender Detail"))


def confirm_trash(selected_senders: list[SenderProfile]) -> bool:
    """Prompt the user to confirm trashing messages from selected senders."""
    total_messages = sum(p.message_count for p in selected_senders)

    lines = ["[bold]The following senders will have their messages trashed:[/bold]", ""]
    for profile in selected_senders:
        lines.append(f"  - {profile.email} ({profile.message_count} messages)")
    lines.append("")
    lines.append(f"[bold]Total messages to trash: {total_messages}[/bold]")

    console.print(Panel("\n".join(lines), title="Confirm Trash"))

    answer = Prompt.ask('[bold red]Type "TRASH" to confirm[/bold red]', console=console)
    return answer == "TRASH"


def display_clean_summary(trashed_count: int, sender_count: int) -> None:
    """Display a success summary after trashing messages."""
    console.print(
        Panel(
            f"[bold green]Successfully trashed {trashed_count} messages "
            f"from {sender_count} senders.[/bold green]",
            title="Done",
        )
    )
