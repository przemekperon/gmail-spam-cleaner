"""Gmail API client functions for fetching and managing messages."""

from __future__ import annotations

import re
from typing import Callable

from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from gmail_spam_cleaner.constants import BATCH_SIZE, METADATA_HEADERS, PAGE_SIZE, TRASH_BATCH_SIZE
from gmail_spam_cleaner.models import MessageMeta

_FROM_RE = re.compile(r"^(.*?)\s*<([^>]+)>$")


def _is_retryable_http_error(exc: BaseException) -> bool:
    return isinstance(exc, HttpError) and exc.resp.status in (429, 500, 503)


def _parse_from_header(from_value: str) -> tuple[str, str]:
    """Parse a From header into (display name, email address).

    Handles formats like:
      "John Doe <john@example.com>" -> ("John Doe", "john@example.com")
      "<john@example.com>"          -> ("", "john@example.com")
      "john@example.com"            -> ("", "john@example.com")
    """
    if not from_value:
        return ("", "")
    m = _FROM_RE.match(from_value.strip())
    if m:
        name = m.group(1).strip().strip('"').strip("'")
        return (name, m.group(2).strip())
    email = from_value.strip().strip("<>")
    return ("", email)


def list_message_ids(
    service,
    query: str | None = None,
    max_results: int | None = None,
) -> list[str]:
    """List all message IDs matching the query, handling pagination."""
    ids: list[str] = []
    page_token: str | None = None

    while True:
        kwargs: dict = {"userId": "me", "maxResults": PAGE_SIZE, "fields": "messages/id,nextPageToken"}
        if query:
            kwargs["query"] = query
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.users().messages().list(**kwargs).execute()
        messages = resp.get("messages", [])
        for msg in messages:
            ids.append(msg["id"])
            if max_results and len(ids) >= max_results:
                return ids[:max_results]

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return ids


@retry(
    retry=retry_if_exception(_is_retryable_http_error),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _execute_batch(batch: BatchHttpRequest) -> None:
    batch.execute()


def fetch_message_metadata(
    service,
    message_ids: list[str],
    callback: Callable[[int, int], None] | None = None,
) -> list[MessageMeta]:
    """Fetch metadata for messages in batches using BatchHttpRequest."""
    results: list[MessageMeta] = []
    total_batches = (len(message_ids) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        start = batch_num * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(message_ids))
        chunk = message_ids[start:end]

        batch = service.new_batch_http_request()

        def _make_callback(msg_id: str):
            def _cb(request_id, response, exception):
                if exception is not None:
                    return
                headers = {}
                for h in response.get("payload", {}).get("headers", []):
                    headers[h["name"]] = h["value"]

                from_value = headers.get("From", "")
                name, email = _parse_from_header(from_value)

                meta = MessageMeta(
                    message_id=msg_id,
                    sender=from_value,
                    sender_email=email.lower(),
                    subject=headers.get("Subject", ""),
                    labels=response.get("labelIds", []),
                    has_list_unsubscribe="List-Unsubscribe" in headers,
                    precedence=headers.get("Precedence", "").lower(),
                    date=headers.get("Date", ""),
                )
                results.append(meta)

            return _cb

        for msg_id in chunk:
            batch.add(
                service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=METADATA_HEADERS,
                ),
                callback=_make_callback(msg_id),
            )

        _execute_batch(batch)

        if callback:
            callback(batch_num + 1, total_batches)

    return results


@retry(
    retry=retry_if_exception(_is_retryable_http_error),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _execute_batch_modify(service, msg_ids: list[str]) -> None:
    service.users().messages().batchModify(
        userId="me",
        body={
            "ids": msg_ids,
            "addLabelIds": ["TRASH"],
            "removeLabelIds": ["INBOX"],
        },
    ).execute()


def trash_messages(
    service,
    message_ids: list[str],
    callback: Callable[[int, int], None] | None = None,
) -> int:
    """Move messages to trash in batches using batchModify."""
    total_batches = max(1, (len(message_ids) + TRASH_BATCH_SIZE - 1) // TRASH_BATCH_SIZE)
    trashed = 0

    for batch_num in range(total_batches):
        start = batch_num * TRASH_BATCH_SIZE
        end = min(start + TRASH_BATCH_SIZE, len(message_ids))
        chunk = message_ids[start:end]
        if not chunk:
            break

        _execute_batch_modify(service, chunk)
        trashed += len(chunk)

        if callback:
            callback(batch_num + 1, total_batches)

    return trashed
