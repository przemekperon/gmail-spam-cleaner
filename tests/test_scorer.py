"""Tests for the scoring module."""

from gmail_spam_cleaner.models import MessageMeta, SenderProfile
from gmail_spam_cleaner.scorer import calculate_score, classify_sender, score_all_senders


def test_newsletter_high_score(newsletter_profile):
    """Newsletter with List-Unsubscribe + noreply@ + bulk + high volume + promotions should score >= 0.7."""
    score = calculate_score(newsletter_profile)
    assert score >= 0.7


def test_personal_low_score(personal_profile):
    """Personal messages from a real person should score < 0.3."""
    score = calculate_score(personal_profile)
    assert score < 0.3


def test_score_capped_at_1():
    """Score should never exceed 1.0 even with all signals present."""
    msgs = [
        MessageMeta(
            message_id=f"msg_{i}",
            sender="Newsletter <noreply@spam.com>",
            sender_email="noreply@spam.com",
            subject=f"Spam #{i}",
            labels=["CATEGORY_PROMOTIONS"],
            has_list_unsubscribe=True,
            precedence="bulk",
        )
        for i in range(20)
    ]
    profile = SenderProfile(
        email="noreply@spam.com",
        name="Newsletter",
        message_count=20,
        messages=msgs,
    )
    score = calculate_score(profile)
    assert score == 1.0


def test_classify_sender_newsletter():
    assert classify_sender(0.9) == "newsletter"
    assert classify_sender(0.7) == "newsletter"


def test_classify_sender_likely():
    assert classify_sender(0.6) == "likely_newsletter"
    assert classify_sender(0.5) == "likely_newsletter"


def test_classify_sender_uncertain():
    assert classify_sender(0.4) == "uncertain"
    assert classify_sender(0.3) == "uncertain"


def test_classify_sender_personal():
    assert classify_sender(0.2) == "personal"
    assert classify_sender(0.0) == "personal"


def test_high_volume_bonus():
    """10+ messages from same sender should add score."""
    msgs = [
        MessageMeta(
            message_id=f"msg_{i}",
            sender="Someone <someone@company.com>",
            sender_email="someone@company.com",
            subject=f"Update #{i}",
        )
        for i in range(10)
    ]
    profile = SenderProfile(
        email="someone@company.com",
        name="Someone",
        message_count=10,
        messages=msgs,
    )
    score = calculate_score(profile)
    # Should get HIGH_VOLUME bonus (0.15)
    assert score >= 0.15


def test_score_all_senders(newsletter_profile, personal_profile):
    """score_all_senders should update all profiles."""
    senders = {
        newsletter_profile.email: newsletter_profile,
        personal_profile.email: personal_profile,
    }
    result = score_all_senders(senders)
    assert result[newsletter_profile.email].score >= 0.7
    assert result[personal_profile.email].score < 0.3


def test_list_unsubscribe_only():
    """Single message with only List-Unsubscribe should get 0.40."""
    msg = MessageMeta(
        message_id="msg_1",
        sender="Service <info@regular-company.com>",
        sender_email="service@regular-company.com",
        subject="Your order confirmation",
        has_list_unsubscribe=True,
    )
    profile = SenderProfile(
        email="service@regular-company.com",
        name="Service",
        message_count=1,
        messages=[msg],
    )
    score = calculate_score(profile)
    assert score == 0.40
