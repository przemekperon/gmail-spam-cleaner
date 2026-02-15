"""Data models for Gmail Spam Cleaner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MessageMeta:
    """Metadata extracted from a single Gmail message."""

    message_id: str
    sender: str  # Full From header value
    sender_email: str  # Extracted email address
    subject: str
    labels: list[str] = field(default_factory=list)
    has_list_unsubscribe: bool = False
    precedence: str = ""  # e.g. "bulk", "list"
    date: str = ""


@dataclass
class SenderProfile:
    """Aggregated profile for a single sender."""

    email: str
    name: str
    message_count: int = 0
    messages: list[MessageMeta] = field(default_factory=list)
    score: float = 0.0
    sample_subjects: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of a mailbox scan."""

    total_messages: int
    senders: dict[str, SenderProfile] = field(default_factory=dict)
    scan_date: str = field(default_factory=lambda: datetime.now().isoformat())
    query: str = ""
