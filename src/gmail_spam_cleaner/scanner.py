"""Scan orchestration - fetches messages, groups by sender, scores."""

from __future__ import annotations

from .cache import ScanCache
from .constants import SAMPLE_SUBJECTS_LIMIT
from .display import console, create_progress
from .gmail_client import fetch_message_metadata, list_message_ids
from .models import MessageMeta, ScanResult, SenderProfile
from .scorer import score_all_senders


def group_by_sender(messages: list[MessageMeta]) -> dict[str, SenderProfile]:
    """Group messages by sender email and build SenderProfile objects."""
    senders: dict[str, SenderProfile] = {}

    for msg in messages:
        email = msg.sender_email
        if email not in senders:
            # Extract name from the first message
            name = msg.sender.split("<")[0].strip().strip('"').strip("'") if "<" in msg.sender else ""
            senders[email] = SenderProfile(email=email, name=name)

        profile = senders[email]
        profile.messages.append(msg)
        profile.message_count += 1

        if len(profile.sample_subjects) < SAMPLE_SUBJECTS_LIMIT and msg.subject:
            profile.sample_subjects.append(msg.subject)

    return senders


def scan_mailbox(
    service,
    query: str | None = None,
    max_results: int | None = None,
    use_cache: bool = True,
    cache_db=None,
) -> ScanResult:
    """Run a full mailbox scan: list IDs, fetch metadata, group, score."""
    with ScanCache(db_path=cache_db) as cache:
        # Try cache first
        if use_cache:
            cached = cache.load_latest_scan(query=query or "")
            if cached:
                console.print(
                    f"[dim]Loaded cached scan from {cached.scan_date} "
                    f"({cached.total_messages} messages, {len(cached.senders)} senders)[/dim]"
                )
                return cached

        # Step 1: List message IDs
        console.print("[bold]Step 1/3:[/bold] Listing message IDs...")
        with create_progress("Listing messages") as progress:
            task = progress.add_task("listing", total=None)
            ids = list_message_ids(service, query=query, max_results=max_results)
            progress.update(task, completed=len(ids), total=len(ids))

        console.print(f"  Found [bold]{len(ids)}[/bold] messages")

        if not ids:
            result = ScanResult(total_messages=0, query=query or "")
            cache.save_scan(result)
            return result

        # Step 2: Fetch metadata
        console.print("[bold]Step 2/3:[/bold] Fetching message metadata...")
        with create_progress("Fetching metadata") as progress:
            total_batches = (len(ids) + 49) // 50
            task = progress.add_task("fetching", total=total_batches)

            def on_batch(batch_num: int, total: int) -> None:
                progress.update(task, completed=batch_num)

            messages = fetch_message_metadata(service, ids, callback=on_batch)

        console.print(f"  Fetched metadata for [bold]{len(messages)}[/bold] messages")

        # Step 3: Group and score
        console.print("[bold]Step 3/3:[/bold] Grouping and scoring senders...")
        senders = group_by_sender(messages)
        senders = score_all_senders(senders)

        result = ScanResult(
            total_messages=len(messages),
            senders=senders,
            query=query or "",
        )

        # Save to cache
        cache.save_scan(result)
        console.print(
            f"  [dim]Saved to cache ({len(senders)} senders)[/dim]"
        )

    return result
