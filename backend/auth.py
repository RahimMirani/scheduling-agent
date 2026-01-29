import os
import json
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

from config import settings

# Token storage path
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")


class GoogleAuth:
    """Handles Google OAuth 2.0 authentication flow."""

    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.flow: Optional[Flow] = None

    def get_credentials_path(self) -> str:
        """Get the path to the credentials.json file."""
        return os.path.join(os.path.dirname(__file__), settings.google_credentials_path)

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid credentials."""
        if self.credentials and self.credentials.valid:
            return True

        # Try to load from saved token
        if os.path.exists(TOKEN_PATH):
            self.credentials = Credentials.from_authorized_user_file(
                TOKEN_PATH, settings.google_scopes
            )
            if self.credentials and self.credentials.valid:
                return True

            # Try to refresh expired credentials
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    return True
                except Exception:
                    # Refresh failed, need to re-authenticate
                    return False

        return False

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Generate the Google OAuth authorization URL."""
        credentials_path = self.get_credentials_path()

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"credentials.json not found at {credentials_path}. "
                "Please download it from Google Cloud Console."
            )

        self.flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=settings.google_scopes,
            redirect_uri=redirect_uri,
        )

        authorization_url, _ = self.flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        return authorization_url

    def handle_callback(self, authorization_response: str) -> bool:
        """Handle the OAuth callback and exchange code for tokens."""
        if not self.flow:
            raise ValueError("OAuth flow not initialized. Call get_authorization_url first.")

        try:
            self.flow.fetch_token(authorization_response=authorization_response)
            self.credentials = self.flow.credentials
            self._save_credentials()
            return True
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            return False

    def _save_credentials(self):
        """Save credentials to token.json file."""
        if self.credentials:
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(self.credentials.to_json())

    def get_credentials(self) -> Optional[Credentials]:
        """Get the current credentials, loading from file if needed."""
        if not self.is_authenticated():
            return None
        return self.credentials

    def logout(self):
        """Clear credentials and remove token file."""
        self.credentials = None
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)


# Singleton instance
google_auth = GoogleAuth()
