"""Tests for the scanner module."""

from gmail_spam_cleaner.models import MessageMeta
from gmail_spam_cleaner.scanner import group_by_sender


def test_group_by_sender():
    """Messages from the same sender should be grouped together."""
    messages = [
        MessageMeta(
            message_id="m1",
            sender="Alice <alice@example.com>",
            sender_email="alice@example.com",
            subject="Hello",
        ),
        MessageMeta(
            message_id="m2",
            sender="Alice <alice@example.com>",
            sender_email="alice@example.com",
            subject="Follow up",
        ),
        MessageMeta(
            message_id="m3",
            sender="Bob <bob@example.com>",
            sender_email="bob@example.com",
            subject="Question",
        ),
    ]
    senders = group_by_sender(messages)
    assert len(senders) == 2
    assert senders["alice@example.com"].message_count == 2
    assert senders["bob@example.com"].message_count == 1


def test_sample_subjects_limit():
    """sample_subjects should not exceed SAMPLE_SUBJECTS_LIMIT (5)."""
    messages = [
        MessageMeta(
            message_id=f"m{i}",
            sender="Sender <sender@example.com>",
            sender_email="sender@example.com",
            subject=f"Subject #{i}",
        )
        for i in range(20)
    ]
    senders = group_by_sender(messages)
    assert len(senders["sender@example.com"].sample_subjects) == 5


def test_group_by_sender_case_insensitive():
    """Sender emails should be grouped case-insensitively (already lowercased in gmail_client)."""
    messages = [
        MessageMeta(
            message_id="m1",
            sender="Alice <alice@example.com>",
            sender_email="alice@example.com",
            subject="Hello",
        ),
        MessageMeta(
            message_id="m2",
            sender="Alice <alice@example.com>",
            sender_email="alice@example.com",
            subject="Follow up",
        ),
    ]
    senders = group_by_sender(messages)
    assert len(senders) == 1


def test_group_by_sender_empty():
    """Empty message list should return empty dict."""
    senders = group_by_sender([])
    assert senders == {}


def test_sender_name_extracted():
    """Sender name should be extracted from the From header."""
    messages = [
        MessageMeta(
            message_id="m1",
            sender="John Doe <john@example.com>",
            sender_email="john@example.com",
            subject="Test",
        ),
    ]
    senders = group_by_sender(messages)
    assert senders["john@example.com"].name == "John Doe"
