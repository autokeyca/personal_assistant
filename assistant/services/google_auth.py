"""Google OAuth2 authentication handler."""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from assistant.config import get


class GoogleAuth:
    """Handle Google OAuth2 authentication."""

    def __init__(self):
        self.credentials_file = get("google.credentials_file")
        self.token_file = get("google.token_file")
        self.scopes = get("google.scopes")
        self._creds = None

    def get_credentials(self) -> Credentials:
        """Get valid credentials, refreshing or re-authenticating if necessary."""
        if self._creds and self._creds.valid:
            return self._creds

        # Try to load from token file
        if os.path.exists(self.token_file):
            self._creds = Credentials.from_authorized_user_file(
                self.token_file, self.scopes
            )

        # Refresh or get new credentials
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Google credentials file not found: {self.credentials_file}\n"
                        "Download it from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                self._creds = flow.run_local_server(port=0)

            # Save credentials
            Path(self.token_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as f:
                f.write(self._creds.to_json())

        return self._creds

    def get_calendar_service(self):
        """Get Google Calendar API service."""
        creds = self.get_credentials()
        return build("calendar", "v3", credentials=creds)

    def get_gmail_service(self):
        """Get Gmail API service."""
        creds = self.get_credentials()
        return build("gmail", "v1", credentials=creds)


# Singleton instance
_auth = None


def get_google_auth() -> GoogleAuth:
    """Get the singleton GoogleAuth instance."""
    global _auth
    if _auth is None:
        _auth = GoogleAuth()
    return _auth
