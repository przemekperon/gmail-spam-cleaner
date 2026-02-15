"""Interactive cleaning workflow - select senders and trash their messages."""

from __future__ import annotations

import json
from datetime import datetime

from .cache import ScanCache
from .constants import TRASH_LOG_PATH
from .display import (
    confirm_trash,
    console,
    create_progress,
    display_clean_summary,
    display_scan_results,
    display_sender_detail,
)
from .gmail_client import trash_messages
from .models import ScanResult, SenderProfile


def _save_trash_log(senders: list[SenderProfile], message_ids: list[str]) -> None:
    """Append a trash action to the audit log."""
    TRASH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    log: list = []
    if TRASH_LOG_PATH.exists():
        with open(TRASH_LOG_PATH) as f:
            try:
                log = json.load(f)
            except json.JSONDecodeError:
                log = []

    entry = {
        "date": datetime.now().isoformat(),
        "senders": [
            {
                "email": s.email,
                "name": s.name,
                "message_count": s.message_count,
            }
            for s in senders
        ],
        "total_messages": len(message_ids),
        "message_ids": message_ids,
    }
    log.append(entry)

    with open(TRASH_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def interactive_clean(
    service,
    scan_result: ScanResult,
    cache_db=None,
    min_score: float = 0.5,
    execute: bool = False,
) -> dict:
    """Run the interactive cleaning workflow.

    Returns a summary dict with keys: selected_senders, total_messages, trashed.
    """
    # Filter out personal senders and sort by message count
    from .constants import SCORE_UNCERTAIN

    from .scorer import classify_sender

    _CLASS_ORDER = {"newsletter": 0, "likely_newsletter": 1, "uncertain": 2}
    profiles = sorted(
        [p for p in scan_result.senders.values() if p.score >= max(min_score, SCORE_UNCERTAIN)],
        key=lambda p: (_CLASS_ORDER.get(classify_sender(p.score), 3), -p.message_count),
    )

    if not profiles:
        console.print(f"[yellow]No senders found with score >= {min_score}[/yellow]")
        return {"selected_senders": 0, "total_messages": 0, "trashed": 0}

    # Display table
    display_scan_results(scan_result, min_score=min_score)

    # Ask user to select senders
    console.print()
    console.print(
        "[bold]Select senders to trash (comma-separated numbers, 'all', or 'q' to quit):[/bold]"
    )
    selection = console.input("> ").strip()

    if selection.lower() == "q":
        console.print("[dim]Cancelled.[/dim]")
        return {"selected_senders": 0, "total_messages": 0, "trashed": 0}

    if selection.lower() == "all":
        selected = profiles
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected = [profiles[i] for i in indices if 0 <= i < len(profiles)]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")
            return {"selected_senders": 0, "total_messages": 0, "trashed": 0}

    if not selected:
        console.print("[yellow]No senders selected.[/yellow]")
        return {"selected_senders": 0, "total_messages": 0, "trashed": 0}

    # Show details of selected senders
    console.print()
    for profile in selected:
        display_sender_detail(profile)

    # Collect message IDs
    with ScanCache(db_path=cache_db) as cache:
        all_message_ids: list[str] = []
        for profile in selected:
            ids = cache.get_message_ids_for_sender(profile.email)
            all_message_ids.extend(ids)

    total_messages = len(all_message_ids)
    console.print(f"\n[bold]Total messages to trash: {total_messages}[/bold]")

    if not execute:
        console.print(
            "\n[yellow][DRY RUN] No messages were trashed. "
            "Use --execute to actually trash messages.[/yellow]"
        )
        return {
            "selected_senders": len(selected),
            "total_messages": total_messages,
            "trashed": 0,
        }

    # Confirm with TRASH
    if not confirm_trash(selected):
        console.print("[dim]Cancelled.[/dim]")
        return {"selected_senders": len(selected), "total_messages": total_messages, "trashed": 0}

    # Trash messages
    with create_progress("Trashing messages") as progress:
        total_batches = max(1, (total_messages + 999) // 1000)
        task = progress.add_task("trashing", total=total_batches)

        def on_batch(batch_num: int, total: int) -> None:
            progress.update(task, completed=batch_num)

        trashed = trash_messages(service, all_message_ids, callback=on_batch)

    # Save audit log
    _save_trash_log(selected, all_message_ids)

    display_clean_summary(trashed, len(selected))

    return {
        "selected_senders": len(selected),
        "total_messages": total_messages,
        "trashed": trashed,
    }
