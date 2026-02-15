"""CLI entry point for Gmail Spam Cleaner."""

from __future__ import annotations

import click

from .auth import check_auth, get_gmail_service
from .cache import ScanCache
from .cleaner import interactive_clean
from .display import console
from .export import export_scan
from .scanner import scan_mailbox


@click.group()
@click.version_option(version="0.1.0", prog_name="gmail-spam-cleaner")
def cli() -> None:
    """Gmail Spam Cleaner - scan and clean newsletters from your Gmail."""


@cli.command()
@click.option("-q", "--query", default=None, help="Gmail search query (e.g. 'before:2024/01/01').")
@click.option("-m", "--max-messages", default=None, type=int, help="Maximum messages to scan.")
@click.option("--no-cache", is_flag=True, help="Skip cache, force fresh scan.")
@click.option("--min-score", default=0.0, type=float, help="Minimum score to display (0.0-1.0).")
def scan(query: str | None, max_messages: int | None, no_cache: bool, min_score: float) -> None:
    """Scan your Gmail inbox and score senders."""
    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e

    result = scan_mailbox(
        service,
        query=query,
        max_results=max_messages,
        use_cache=not no_cache,
    )

    from .display import display_scan_results

    display_scan_results(result, min_score=min_score)


@cli.command()
@click.option("--execute", is_flag=True, help="Actually trash messages (default is dry-run).")
@click.option("--min-score", default=0.5, type=float, help="Minimum score threshold (default 0.5).")
def clean(execute: bool, min_score: float) -> None:
    """Interactively select senders and trash their messages."""
    # Try loading from cache first
    with ScanCache() as cache:
        scan_result = cache.load_latest_scan()

    if not scan_result:
        console.print("[yellow]No cached scan found. Running a scan first...[/yellow]")
        try:
            service = get_gmail_service()
        except FileNotFoundError as e:
            raise click.ClickException(str(e)) from e
        scan_result = scan_mailbox(service)
    else:
        console.print(
            f"[dim]Using cached scan from {scan_result.scan_date} "
            f"({scan_result.total_messages} messages)[/dim]"
        )

    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        if execute:
            raise click.ClickException(str(e)) from e
        service = None  # dry-run doesn't need service

    interactive_clean(
        service,
        scan_result,
        min_score=min_score,
        execute=execute,
    )


@cli.command(name="export")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Output format.",
)
@click.option("-o", "--output", required=True, help="Output file path.")
def export_cmd(fmt: str, output: str) -> None:
    """Export scan results to CSV or JSON."""
    with ScanCache() as cache:
        scan_result = cache.load_latest_scan()

    if not scan_result:
        raise click.ClickException("No cached scan found. Run 'scan' first.")

    export_scan(scan_result, format=fmt, output_path=output)


@cli.command()
def auth() -> None:
    """Test or reset Gmail authentication."""
    check_auth()


@cli.group(name="cache")
def cache_group() -> None:
    """Manage the scan cache."""


@cache_group.command(name="info")
def cache_info() -> None:
    """Show cache statistics."""
    with ScanCache() as cache:
        info = cache.get_info()

    if info["last_scan_date"] is None:
        console.print("[dim]Cache is empty.[/dim]")
        return

    console.print(f"[bold]Database size:[/bold] {info['db_file_size'] / 1024:.1f} KB")
    console.print(f"[bold]Last scan:[/bold] {info['last_scan_date']}")
    console.print(f"[bold]Senders:[/bold] {info['sender_count']}")
    console.print(f"[bold]Messages:[/bold] {info['message_count']}")


@cache_group.command(name="clear")
def cache_clear() -> None:
    """Clear the scan cache."""
    with ScanCache() as cache:
        cache.clear()
    console.print("[green]Cache cleared.[/green]")
