# Gmail Spam Cleaner

A command-line tool that scans your Gmail inbox, identifies newsletters and automated messages using a multi-signal scoring system, and lets you interactively bulk-trash them — safely and reversibly.

Built for anyone drowning in years of accumulated subscriptions, promotions, and notification emails.

## How It Works

Gmail Spam Cleaner operates in two phases:

**Phase 1 — Scan:** Connects to Gmail via API, fetches message metadata (not content), groups messages by sender, and scores each sender on a 0.0–1.0 scale indicating how likely they are to be a newsletter or automated sender.

**Phase 2 — Clean:** Presents an interactive table of scored senders. You pick which ones to trash. Messages are moved to Gmail's Trash (recoverable for 30 days), never permanently deleted.

```
$ gmail-spam-cleaner scan

Step 1/3: Listing message IDs...
  Found 12,847 messages
Step 2/3: Fetching message metadata...
Step 3/3: Grouping and scoring senders...

┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃  # ┃ Email                           ┃ Name              ┃ Count ┃ Score ┃ Classification    ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│  1 │ noreply@medium.com              │ Medium Daily      │   482 │  1.00 │ newsletter        │
│  2 │ newsletter@example.com          │ Weekly Digest     │   231 │  0.90 │ newsletter        │
│  3 │ notifications@github.com        │ GitHub            │  1024 │  0.70 │ newsletter        │
│  … │                                 │                   │       │       │                   │
│ 89 │ alice@gmail.com                 │ Alice Smith       │    14 │  0.15 │ personal          │
└────┴─────────────────────────────────┴───────────────────┴───────┴───────┴───────────────────┘
```

## Safety First

This tool is designed to **never delete your real conversations**. Six layers of protection ensure that:

| Layer | Protection |
|-------|-----------|
| **OAuth scope** | Uses `gmail.modify` — cannot permanently delete emails (no `mail.google.com` scope) |
| **Dry-run by default** | `clean` without `--execute` only shows what *would* be trashed |
| **Score threshold** | Only senders scoring ≥ 0.5 are shown during cleanup by default |
| **Interactive confirmation** | You hand-pick senders, then type `TRASH` to confirm |
| **Recoverable** | Messages go to Trash — 30 days to recover them in Gmail |
| **Audit log** | Every action is logged to `~/.gmail-spam-cleaner/trash_log.json` |

## Scoring System

Each sender is scored using five signals. Higher score = more likely to be a newsletter:

| Signal | Weight | Description |
|--------|--------|-------------|
| `List-Unsubscribe` header | +0.40 | Strongest indicator — required for bulk senders since Feb 2024 |
| Automated sender pattern | +0.20 | Addresses like `noreply@`, `newsletter@`, `notifications@`, etc. |
| `Precedence: bulk` header | +0.15 | Standard header for mass-sent email |
| High volume (10+ messages) | +0.15 | Newsletters send frequently |
| Gmail's Promotions category | +0.10 | Google's own classification |

**Classification thresholds:**
- `≥ 0.7` — Newsletter (almost certainly automated)
- `≥ 0.5` — Likely newsletter
- `≥ 0.3` — Uncertain
- `< 0.3` — Personal (real human conversation)

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/user/gmail-spam-cleaner.git
cd gmail-spam-cleaner
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Setup

You need OAuth credentials from Google Cloud Console. One-time setup (~3 minutes):

### 1. Create a Google Cloud project

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project (e.g., "Gmail Spam Cleaner")

### 2. Enable the Gmail API

- Navigate to **APIs & Services → Library**
- Search for "Gmail API" → click **Enable**

### 3. Configure OAuth consent screen

- Go to **APIs & Services → OAuth consent screen**
- Select **External** → **Create**
- Fill in the required fields (app name, support email, developer email)
- Under **Scopes**, add `https://www.googleapis.com/auth/gmail.modify`
- Under **Test users**, add your Gmail address
- Save

### 4. Create credentials

- Go to **APIs & Services → Credentials**
- Click **Create Credentials → OAuth client ID**
- Application type: **Desktop app**
- Click **Create**, then **Download JSON**

### 5. Place the credentials file

```bash
mkdir -p ~/.gmail-spam-cleaner
mv ~/Downloads/client_secret_*.json ~/.gmail-spam-cleaner/credentials.json
```

### 6. Authenticate

```bash
gmail-spam-cleaner auth
# Opens browser → sign in → grant access
# Output: Authenticated as you@gmail.com
```

> **Note:** In "Testing" mode, tokens expire every 7 days. You'll need to re-authenticate occasionally. This is fine for personal use — no Google verification needed.

## Usage

### Scan your inbox

```bash
# Full scan
gmail-spam-cleaner scan

# Only messages before 2024
gmail-spam-cleaner scan -q "before:2024/01/01"

# Limit to 5000 messages
gmail-spam-cleaner scan -m 5000

# Force fresh scan (skip cache)
gmail-spam-cleaner scan --no-cache

# Show only high-confidence newsletters
gmail-spam-cleaner scan --min-score 0.7
```

### Clean up

```bash
# Dry run — see what would be trashed (safe, no changes made)
gmail-spam-cleaner clean

# Only show senders with score ≥ 0.7
gmail-spam-cleaner clean --min-score 0.7

# Actually trash selected messages
gmail-spam-cleaner clean --execute
```

The interactive flow:

1. A table of scored senders is displayed
2. You enter sender numbers to trash (e.g., `1,3,5,12` or `all`)
3. Sample subjects are shown for review
4. You type `TRASH` to confirm (or anything else to cancel)

### Export results

```bash
# Export to CSV
gmail-spam-cleaner export --format csv -o report.csv

# Export to JSON
gmail-spam-cleaner export --format json -o report.json
```

### Cache management

Scan results are cached locally in SQLite so you don't re-scan every time.

```bash
# Show cache info
gmail-spam-cleaner cache info

# Clear cache
gmail-spam-cleaner cache clear
```

## Performance

- **Message listing:** 500 IDs per API page, handles pagination automatically
- **Metadata fetching:** Batched 50 messages per request via `BatchHttpRequest`
- **Trashing:** 1,000 messages per `batchModify` call
- **Metadata only:** Only headers are fetched — message bodies are never downloaded
- **Caching:** SQLite cache means subsequent runs are instant
- **Rate limiting:** Automatic exponential backoff with `tenacity` for API quota limits

A mailbox with 10,000 messages typically scans in under 2 minutes.

## Project Structure

```
src/gmail_spam_cleaner/
├── cli.py              # Click CLI — scan, clean, export, auth, cache commands
├── auth.py             # OAuth2 flow (gmail.modify scope)
├── gmail_client.py     # Gmail API wrapper — list, batch get, batch trash
├── scanner.py          # Scan orchestration — fetch, group, score
├── scorer.py           # Multi-signal newsletter scoring (0.0–1.0)
├── cleaner.py          # Interactive selection + trash workflow
├── cache.py            # SQLite cache for scan results
├── models.py           # Data models — MessageMeta, SenderProfile, ScanResult
├── display.py          # Rich tables, progress bars, confirmations
├── export.py           # CSV/JSON export
└── constants.py        # Scoring weights, API limits, sender patterns
```

## Configuration

All configuration files are stored in `~/.gmail-spam-cleaner/`:

| File | Description |
|------|-------------|
| `credentials.json` | OAuth client credentials (you provide this) |
| `token.json` | Access token (auto-generated on first auth) |
| `cache.db` | SQLite scan results cache |
| `trash_log.json` | Audit log of all trash operations |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## License

MIT
