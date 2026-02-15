"""SQLite cache for storing scan results."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from gmail_spam_cleaner.constants import CACHE_DB_PATH
from gmail_spam_cleaner.models import MessageMeta, ScanResult, SenderProfile

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS scan_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT,
    total_messages INTEGER,
    scan_date TEXT
);

CREATE TABLE IF NOT EXISTS senders (
    scan_id INTEGER,
    email TEXT,
    name TEXT,
    message_count INTEGER,
    score REAL,
    sample_subjects_json TEXT,
    FOREIGN KEY (scan_id) REFERENCES scan_metadata(id)
);

CREATE TABLE IF NOT EXISTS messages (
    scan_id INTEGER,
    message_id TEXT,
    sender_email TEXT,
    subject TEXT,
    has_list_unsubscribe INTEGER,
    precedence TEXT,
    labels_json TEXT,
    date TEXT,
    FOREIGN KEY (scan_id) REFERENCES scan_metadata(id)
);
"""


class ScanCache:
    """Persistent SQLite cache for scan results."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or CACHE_DB_PATH
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(_CREATE_TABLES_SQL)

    # --- public API ---

    def save_scan(self, scan_result: ScanResult) -> None:
        """Save a full scan result in a single transaction."""
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO scan_metadata (query, total_messages, scan_date) VALUES (?, ?, ?)",
                (scan_result.query, scan_result.total_messages, scan_result.scan_date),
            )
            scan_id = cursor.lastrowid

            for profile in scan_result.senders.values():
                self._conn.execute(
                    "INSERT INTO senders (scan_id, email, name, message_count, score, sample_subjects_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        scan_id,
                        profile.email,
                        profile.name,
                        profile.message_count,
                        profile.score,
                        json.dumps(profile.sample_subjects),
                    ),
                )

                for msg in profile.messages:
                    self._conn.execute(
                        "INSERT INTO messages (scan_id, message_id, sender_email, subject, "
                        "has_list_unsubscribe, precedence, labels_json, date) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            scan_id,
                            msg.message_id,
                            msg.sender_email,
                            msg.subject,
                            int(msg.has_list_unsubscribe),
                            msg.precedence,
                            json.dumps(msg.labels),
                            msg.date,
                        ),
                    )

    def load_latest_scan(self, query: str | None = None) -> ScanResult | None:
        """Load the most recent scan, optionally filtered by query."""
        if query is not None:
            row = self._conn.execute(
                "SELECT * FROM scan_metadata WHERE query = ? ORDER BY id DESC LIMIT 1",
                (query,),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM scan_metadata ORDER BY id DESC LIMIT 1"
            ).fetchone()

        if row is None:
            return None

        scan_id = row["id"]

        sender_rows = self._conn.execute(
            "SELECT * FROM senders WHERE scan_id = ?", (scan_id,)
        ).fetchall()

        message_rows = self._conn.execute(
            "SELECT * FROM messages WHERE scan_id = ?", (scan_id,)
        ).fetchall()

        # Group messages by sender_email
        messages_by_sender: dict[str, list[MessageMeta]] = {}
        for m in message_rows:
            meta = MessageMeta(
                message_id=m["message_id"],
                sender="",
                sender_email=m["sender_email"],
                subject=m["subject"],
                labels=json.loads(m["labels_json"]),
                has_list_unsubscribe=bool(m["has_list_unsubscribe"]),
                precedence=m["precedence"],
                date=m["date"],
            )
            messages_by_sender.setdefault(m["sender_email"], []).append(meta)

        senders: dict[str, SenderProfile] = {}
        for s in sender_rows:
            email = s["email"]
            senders[email] = SenderProfile(
                email=email,
                name=s["name"],
                message_count=s["message_count"],
                messages=messages_by_sender.get(email, []),
                score=s["score"],
                sample_subjects=json.loads(s["sample_subjects_json"]),
            )

        return ScanResult(
            total_messages=row["total_messages"],
            senders=senders,
            scan_date=row["scan_date"],
            query=row["query"] or "",
        )

    def get_message_ids_for_sender(self, email: str) -> list[str]:
        """Return all message IDs for a sender from the latest scan."""
        row = self._conn.execute(
            "SELECT id FROM scan_metadata ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return []

        rows = self._conn.execute(
            "SELECT message_id FROM messages WHERE scan_id = ? AND sender_email = ?",
            (row["id"], email),
        ).fetchall()
        return [r["message_id"] for r in rows]

    def clear(self) -> None:
        """Drop and recreate all tables."""
        self._conn.executescript(
            "DROP TABLE IF EXISTS messages;"
            "DROP TABLE IF EXISTS senders;"
            "DROP TABLE IF EXISTS scan_metadata;"
        )
        self._create_tables()

    def get_info(self) -> dict:
        """Return cache statistics."""
        file_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        last_scan_row = self._conn.execute(
            "SELECT scan_date FROM scan_metadata ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_scan_date = last_scan_row["scan_date"] if last_scan_row else None

        sender_count = self._conn.execute("SELECT COUNT(*) AS c FROM senders").fetchone()["c"]
        message_count = self._conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]

        return {
            "db_file_size": file_size,
            "last_scan_date": last_scan_date,
            "sender_count": sender_count,
            "message_count": message_count,
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # --- context manager ---

    def __enter__(self) -> ScanCache:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.close()
