"""Shared fixtures for tests."""

from __future__ import annotations

import pytest

from gmail_spam_cleaner.models import MessageMeta, ScanResult, SenderProfile


@pytest.fixture
def newsletter_message() -> MessageMeta:
    return MessageMeta(
        message_id="msg_nl_001",
        sender="Newsletter Team <noreply@example-newsletter.com>",
        sender_email="noreply@example-newsletter.com",
        subject="Weekly Digest: Top Stories This Week",
        labels=["INBOX", "CATEGORY_PROMOTIONS"],
        has_list_unsubscribe=True,
        precedence="bulk",
        date="2024-01-15",
    )


@pytest.fixture
def personal_message() -> MessageMeta:
    return MessageMeta(
        message_id="msg_ps_001",
        sender="Alice Smith <alice.smith@gmail.com>",
        sender_email="alice.smith@gmail.com",
        subject="Re: Lunch tomorrow?",
        labels=["INBOX"],
        has_list_unsubscribe=False,
        precedence="",
        date="2024-06-01",
    )


@pytest.fixture
def newsletter_profile(newsletter_message: MessageMeta) -> SenderProfile:
    msgs = [newsletter_message]
    # Add more messages to reach high volume
    for i in range(14):
        msgs.append(
            MessageMeta(
                message_id=f"msg_nl_{i+2:03d}",
                sender="Newsletter Team <noreply@example-newsletter.com>",
                sender_email="noreply@example-newsletter.com",
                subject=f"Newsletter #{i+2}",
                labels=["INBOX", "CATEGORY_PROMOTIONS"],
                has_list_unsubscribe=True,
                precedence="bulk",
                date=f"2024-01-{i+2:02d}",
            )
        )
    return SenderProfile(
        email="noreply@example-newsletter.com",
        name="Newsletter Team",
        message_count=15,
        messages=msgs,
        sample_subjects=["Weekly Digest: Top Stories This Week"] + [f"Newsletter #{i}" for i in range(2, 6)],
    )


@pytest.fixture
def personal_profile(personal_message: MessageMeta) -> SenderProfile:
    return SenderProfile(
        email="alice.smith@gmail.com",
        name="Alice Smith",
        message_count=3,
        messages=[
            personal_message,
            MessageMeta(
                message_id="msg_ps_002",
                sender="Alice Smith <alice.smith@gmail.com>",
                sender_email="alice.smith@gmail.com",
                subject="Meeting notes",
                labels=["INBOX"],
            ),
            MessageMeta(
                message_id="msg_ps_003",
                sender="Alice Smith <alice.smith@gmail.com>",
                sender_email="alice.smith@gmail.com",
                subject="Photos from the trip",
                labels=["INBOX"],
            ),
        ],
        sample_subjects=["Re: Lunch tomorrow?", "Meeting notes", "Photos from the trip"],
    )


@pytest.fixture
def sample_scan_result(newsletter_profile: SenderProfile, personal_profile: SenderProfile) -> ScanResult:
    return ScanResult(
        total_messages=18,
        senders={
            newsletter_profile.email: newsletter_profile,
            personal_profile.email: personal_profile,
        },
        query="",
    )
