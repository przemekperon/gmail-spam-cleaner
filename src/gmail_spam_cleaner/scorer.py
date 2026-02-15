"""Scoring and classification of senders."""

from .constants import (
    AUTOMATED_SENDER_PATTERNS,
    HIGH_VOLUME_THRESHOLD,
    SCORE_LIKELY_NEWSLETTER,
    SCORE_NEWSLETTER,
    SCORE_UNCERTAIN,
    WEIGHT_CATEGORY_PROMOTIONS,
    WEIGHT_HIGH_VOLUME,
    WEIGHT_LIST_UNSUBSCRIBE,
    WEIGHT_PRECEDENCE_BULK,
    WEIGHT_SENDER_PATTERN,
)
from .models import SenderProfile


def calculate_score(profile: SenderProfile) -> float:
    """Calculate a spam/newsletter score for a sender profile.

    Returns a float between 0.0 and 1.0.
    """
    total = 0.0

    if any(m.has_list_unsubscribe for m in profile.messages):
        total += WEIGHT_LIST_UNSUBSCRIBE

    if any(
        profile.email.lower().startswith(pattern)
        for pattern in AUTOMATED_SENDER_PATTERNS
    ):
        total += WEIGHT_SENDER_PATTERN

    if any(m.precedence.lower() in ("bulk", "list") for m in profile.messages):
        total += WEIGHT_PRECEDENCE_BULK

    if profile.message_count >= HIGH_VOLUME_THRESHOLD:
        total += WEIGHT_HIGH_VOLUME

    if any("CATEGORY_PROMOTIONS" in m.labels for m in profile.messages):
        total += WEIGHT_CATEGORY_PROMOTIONS

    return min(total, 1.0)


def classify_sender(score: float) -> str:
    """Classify a sender based on their score."""
    if score >= SCORE_NEWSLETTER:
        return "newsletter"
    if score >= SCORE_LIKELY_NEWSLETTER:
        return "likely_newsletter"
    if score >= SCORE_UNCERTAIN:
        return "uncertain"
    return "personal"


def score_all_senders(
    senders: dict[str, SenderProfile],
) -> dict[str, SenderProfile]:
    """Calculate scores for all sender profiles and update them in place."""
    for profile in senders.values():
        profile.score = calculate_score(profile)
    return senders
