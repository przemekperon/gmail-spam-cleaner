"""Tests for the SQLite cache module."""

from gmail_spam_cleaner.cache import ScanCache
from gmail_spam_cleaner.models import MessageMeta, ScanResult, SenderProfile


def test_save_and_load(tmp_path):
    """Save a ScanResult and load it back."""
    db_path = tmp_path / "test_cache.db"

    msg = MessageMeta(
        message_id="m1",
        sender="Test <test@example.com>",
        sender_email="test@example.com",
        subject="Test subject",
        labels=["INBOX"],
        has_list_unsubscribe=True,
        precedence="bulk",
        date="2024-01-01",
    )

    profile = SenderProfile(
        email="test@example.com",
        name="Test",
        message_count=1,
        messages=[msg],
        score=0.55,
        sample_subjects=["Test subject"],
    )

    scan = ScanResult(
        total_messages=1,
        senders={"test@example.com": profile},
        query="test query",
    )

    with ScanCache(db_path=db_path) as cache:
        cache.save_scan(scan)
        loaded = cache.load_latest_scan()

    assert loaded is not None
    assert loaded.total_messages == 1
    assert loaded.query == "test query"
    assert "test@example.com" in loaded.senders
    loaded_profile = loaded.senders["test@example.com"]
    assert loaded_profile.name == "Test"
    assert loaded_profile.message_count == 1
    assert loaded_profile.score == 0.55
    assert loaded_profile.sample_subjects == ["Test subject"]
    assert len(loaded_profile.messages) == 1
    assert loaded_profile.messages[0].message_id == "m1"
    assert loaded_profile.messages[0].has_list_unsubscribe is True


def test_get_message_ids_for_sender(tmp_path):
    """Get message IDs for a specific sender."""
    db_path = tmp_path / "test_cache.db"

    msgs = [
        MessageMeta(
            message_id=f"m{i}",
            sender="Sender <sender@example.com>",
            sender_email="sender@example.com",
            subject=f"Subject {i}",
        )
        for i in range(3)
    ]

    profile = SenderProfile(
        email="sender@example.com",
        name="Sender",
        message_count=3,
        messages=msgs,
        score=0.5,
        sample_subjects=["Subject 0"],
    )

    scan = ScanResult(
        total_messages=3,
        senders={"sender@example.com": profile},
    )

    with ScanCache(db_path=db_path) as cache:
        cache.save_scan(scan)
        ids = cache.get_message_ids_for_sender("sender@example.com")

    assert sorted(ids) == ["m0", "m1", "m2"]


def test_clear(tmp_path):
    """Clearing cache should remove all data."""
    db_path = tmp_path / "test_cache.db"

    scan = ScanResult(total_messages=0, senders={})

    with ScanCache(db_path=db_path) as cache:
        cache.save_scan(scan)
        assert cache.load_latest_scan() is not None
        cache.clear()
        assert cache.load_latest_scan() is None


def test_get_info(tmp_path):
    """Cache info should return correct stats."""
    db_path = tmp_path / "test_cache.db"

    msg = MessageMeta(
        message_id="m1",
        sender="Test <test@example.com>",
        sender_email="test@example.com",
        subject="Test",
    )

    profile = SenderProfile(
        email="test@example.com",
        name="Test",
        message_count=1,
        messages=[msg],
        score=0.5,
        sample_subjects=["Test"],
    )

    scan = ScanResult(
        total_messages=1,
        senders={"test@example.com": profile},
    )

    with ScanCache(db_path=db_path) as cache:
        cache.save_scan(scan)
        info = cache.get_info()

    assert info["sender_count"] == 1
    assert info["message_count"] == 1
    assert info["last_scan_date"] is not None
    assert info["db_file_size"] > 0


def test_load_latest_scan_with_query(tmp_path):
    """Loading with query filter should return matching scan."""
    db_path = tmp_path / "test_cache.db"

    scan1 = ScanResult(total_messages=5, senders={}, query="before:2024/01/01")
    scan2 = ScanResult(total_messages=10, senders={}, query="")

    with ScanCache(db_path=db_path) as cache:
        cache.save_scan(scan1)
        cache.save_scan(scan2)

        latest_all = cache.load_latest_scan()
        assert latest_all is not None
        assert latest_all.total_messages == 10

        latest_query = cache.load_latest_scan(query="before:2024/01/01")
        assert latest_query is not None
        assert latest_query.total_messages == 5


def test_empty_cache(tmp_path):
    """Empty cache should return None."""
    db_path = tmp_path / "test_cache.db"

    with ScanCache(db_path=db_path) as cache:
        assert cache.load_latest_scan() is None
        assert cache.get_message_ids_for_sender("nobody@example.com") == []
