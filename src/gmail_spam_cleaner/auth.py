"""Authentication helpers for Gmail API."""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from gmail_spam_cleaner.constants import CONFIG_DIR, CREDENTIALS_PATH, SCOPES, TOKEN_PATH


def get_gmail_service() -> Resource:
    """Return an authenticated Gmail API service object.

    Loads cached token from TOKEN_PATH if available.  When the token is
    expired it is silently refreshed.  If no token exists, an OAuth
    browser flow is launched (requires credentials.json at
    CREDENTIALS_PATH).
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Credentials file not found at {CREDENTIALS_PATH}.\n"
                "Download your OAuth client credentials from the Google Cloud Console "
                "and save them as:\n"
                f"  {CREDENTIALS_PATH}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def check_auth() -> bool:
    """Test whether Gmail authentication is working.

    Returns True when the service can reach the Gmail API, False otherwise.
    Prints human-readable status messages.
    """
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        print(f"Authenticated as {profile['emailAddress']}")
        return True
    except FileNotFoundError as exc:
        print(f"Authentication failed: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"Authentication failed: {exc}")
        return False
