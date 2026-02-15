"""Constants for Gmail Spam Cleaner."""

from pathlib import Path

# --- Config paths ---
CONFIG_DIR = Path.home() / ".gmail-spam-cleaner"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
TOKEN_PATH = CONFIG_DIR / "token.json"
CACHE_DB_PATH = CONFIG_DIR / "cache.db"
TRASH_LOG_PATH = CONFIG_DIR / "trash_log.json"

# --- Gmail API ---
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
BATCH_SIZE = 50  # messages per BatchHttpRequest
PAGE_SIZE = 500  # messages per list page
TRASH_BATCH_SIZE = 1000  # messages per batchModify call
METADATA_HEADERS = ["From", "Subject", "List-Unsubscribe", "Precedence"]

# --- Scoring weights ---
WEIGHT_LIST_UNSUBSCRIBE = 0.40
WEIGHT_SENDER_PATTERN = 0.20
WEIGHT_PRECEDENCE_BULK = 0.15
WEIGHT_HIGH_VOLUME = 0.15
WEIGHT_CATEGORY_PROMOTIONS = 0.10

# --- Scoring thresholds ---
SCORE_NEWSLETTER = 0.7
SCORE_LIKELY_NEWSLETTER = 0.5
SCORE_UNCERTAIN = 0.3
HIGH_VOLUME_THRESHOLD = 10  # messages from one sender

# --- Sender patterns (automated/newsletter addresses) ---
AUTOMATED_SENDER_PATTERNS = [
    "noreply@",
    "no-reply@",
    "newsletter@",
    "newsletters@",
    "notifications@",
    "notification@",
    "info@",
    "mailer@",
    "marketing@",
    "news@",
    "updates@",
    "update@",
    "do-not-reply@",
    "donotreply@",
    "alert@",
    "alerts@",
    "digest@",
    "hello@",
    "support@",
    "team@",
    "mail@",
    "bounce@",
    "auto@",
]

# --- Display ---
SAMPLE_SUBJECTS_LIMIT = 5
