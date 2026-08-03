# gmail_reader.py — Gmail API authentication and email fetching
#
# First run: opens a browser window for you to authorize access.
# After that, saves a token.json so you stay logged in automatically.

import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only access to Gmail is all we need
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Absolute paths so these files resolve no matter what directory Flask runs from
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE  = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE  = os.path.join(BASE_DIR, "token.json")


def get_gmail_service():
    """Authenticate with Gmail and return a service object.
    Saves credentials to token.json after the first login."""
    creds = None

    # Reuse existing token if we have one
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid token, go through the OAuth flow
    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed = True
            except Exception:
                # Refresh token dead/revoked (common in OAuth "testing" mode) —
                # delete the stale token and fall back to a fresh login.
                creds = None
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)

        if not refreshed:
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found. Gmail scan only works locally "
                    "with your Google OAuth credentials file in the project folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_email_body(msg):
    """Extract plain text from a Gmail message payload."""
    payload = msg.get("payload", {})

    # Single-part message
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

    # Multi-part message — find the text/plain part
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


def fetch_recent_emails(max_results=15):
    """Fetch recent emails from your inbox.
    Returns a list of dicts: {id, subject, sender, body, snippet}"""
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        labelIds=["INBOX"],
    ).execute()

    emails = []
    for msg_ref in results.get("messages", []):
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="full",
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": headers.get("From", "Unknown"),
            "body": get_email_body(msg),
            "snippet": msg.get("snippet", ""),
        })

    return emails
