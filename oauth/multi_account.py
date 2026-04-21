"""
Multi-Account Manager for Google Ads MCP Server.

Stores one OAuth token per Google user/login, enabling seamless
switching between multiple advertisers or agencies without
re-authentication.

Storage layout (project root):
  google_ads_accounts.json   → account registry
  tokens/<label>_token.json  → one token file per account
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("google_ads_multi_account")

SCOPES = ["https://www.googleapis.com/auth/adwords"]

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_ACCOUNTS_FILE = os.path.join(_BASE_DIR, "google_ads_accounts.json")


class MultiAccountManager:
    """Manages OAuth credentials for multiple Google Ads accounts."""

    def __init__(self, accounts_file: str = _DEFAULT_ACCOUNTS_FILE):
        self.accounts_file = accounts_file
        self.tokens_dir = os.path.join(os.path.dirname(accounts_file), "tokens")
        self._data: Dict[str, Any] = {"active_account": None, "accounts": {}}
        self._load()

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load accounts file: {e}")
                self._data = {"active_account": None, "accounts": {}}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
        with open(self.accounts_file, "w") as f:
            json.dump(self._data, f, indent=2)

    # ------------------------------------------------------------------ #
    #  Account CRUD                                                        #
    # ------------------------------------------------------------------ #

    def add_account(
        self,
        label: str,
        credentials_path: str,
        display_name: str = "",
        default_customer_id: str = "",
    ) -> Dict[str, Any]:
        """
        Add (or re-authenticate) a Google Ads account via OAuth.

        Opens a browser window for the user to authorise the app.
        On success the token is saved to tokens/<label>_token.json and
        the account becomes available for all tool calls.

        Args:
            label:               Unique short name (e.g. "client_a", "agency").
            credentials_path:    Path to the OAuth client_secret JSON downloaded
                                 from Google Cloud Console.
            display_name:        Optional human-readable name.
            default_customer_id: Default Google Ads customer ID for this login.

        Returns:
            Dict with success status and account details.
        """
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_path}\n"
                "Download it from Google Cloud Console → APIs & Services → Credentials."
            )

        os.makedirs(self.tokens_dir, exist_ok=True)
        token_file = os.path.join(self.tokens_dir, f"{label}_token.json")

        logger.info(f"Starting OAuth flow for account label: '{label}'")
        creds = self._load_or_refresh(token_file)

        if not creds:
            creds = self._run_oauth_flow(credentials_path)
            self._write_token(creds, token_file)

        account_info: Dict[str, Any] = {
            "label": label,
            "display_name": display_name or label,
            "credentials_path": credentials_path,
            "token_file": token_file,
            "default_customer_id": default_customer_id,
        }
        self._data["accounts"][label] = account_info

        if self._data["active_account"] is None:
            self._data["active_account"] = label

        self._save()
        logger.info(f"Account '{label}' added successfully.")

        return {
            "success": True,
            "message": (
                f"Account '{label}' authenticated successfully. "
                f"{'(set as active)' if self._data['active_account'] == label else ''}"
            ),
            "account": account_info,
            "is_active": self._data["active_account"] == label,
        }

    def set_active_account(self, label: str) -> Dict[str, Any]:
        """Switch the active account used by default for all API calls."""
        self._assert_exists(label)
        self._data["active_account"] = label
        self._save()
        return {
            "success": True,
            "active_account": label,
            "account": self._data["accounts"][label],
        }

    def list_accounts(self) -> List[Dict[str, Any]]:
        """Return all configured accounts with their status."""
        active = self._data.get("active_account")
        result = []
        for label, info in self._data["accounts"].items():
            entry = dict(info)
            entry["is_active"] = label == active
            entry["token_exists"] = os.path.exists(info.get("token_file", ""))
            result.append(entry)
        return result

    def remove_account(self, label: str) -> Dict[str, Any]:
        """Remove an account and delete its saved token."""
        self._assert_exists(label)
        account = self._data["accounts"].pop(label)

        token_file = account.get("token_file", "")
        if token_file and os.path.exists(token_file):
            try:
                os.remove(token_file)
            except Exception as e:
                logger.warning(f"Could not delete token file: {e}")

        if self._data["active_account"] == label:
            remaining = list(self._data["accounts"].keys())
            self._data["active_account"] = remaining[0] if remaining else None

        self._save()
        return {
            "success": True,
            "removed": label,
            "new_active_account": self._data["active_account"],
        }

    # ------------------------------------------------------------------ #
    #  Credentials & Headers                                               #
    # ------------------------------------------------------------------ #

    def get_credentials(self, label: str = None) -> Credentials:
        """
        Return valid OAuth credentials for the specified account (or active).
        Automatically refreshes expired tokens; re-runs OAuth if refresh fails.
        """
        if label is None:
            label = self._data.get("active_account")
        if not label:
            raise ValueError(
                "No account configured. "
                "Call add_google_account(label, credentials_path) first."
            )
        self._assert_exists(label)

        account = self._data["accounts"][label]
        token_file = account.get("token_file", "")
        credentials_path = account.get("credentials_path", "")

        creds = self._load_or_refresh(token_file)
        if creds:
            return creds

        # Token expired and refresh failed – need full re-auth
        if not credentials_path or not os.path.exists(credentials_path):
            raise ValueError(
                f"Token for account '{label}' is expired and the credentials "
                f"file is missing ({credentials_path}). "
                f"Re-authenticate with add_google_account('{label}', credentials_path='...')."
            )

        creds = self._run_oauth_flow(credentials_path)
        self._write_token(creds, token_file)
        return creds

    def get_headers(
        self,
        label: str = None,
        manager_customer_id: str = None,
    ) -> Dict[str, str]:
        """Build HTTP headers for a Google Ads REST API call."""
        developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        if not developer_token:
            raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN not set in environment.")

        creds = self.get_credentials(label)

        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Developer-Token": developer_token.strip('"').strip("'"),
            "Content-Type": "application/json",
        }

        if manager_customer_id:
            from .google_auth import format_customer_id
            headers["login-customer-id"] = format_customer_id(manager_customer_id)

        return headers

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _assert_exists(self, label: str) -> None:
        if label not in self._data["accounts"]:
            available = list(self._data["accounts"].keys())
            raise ValueError(
                f"Account '{label}' not found. Available: {available or 'none'}"
            )

    def _load_or_refresh(self, token_file: str) -> Optional[Credentials]:
        """Load token from file; refresh if expired. Returns None if unusable."""
        if not os.path.exists(token_file):
            return None
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logger.warning(f"Could not load token file {token_file}: {e}")
            return None

        if creds.valid:
            return creds

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._write_token(creds, token_file)
                logger.info(f"Token refreshed: {token_file}")
                return creds
            except (RefreshError, Exception) as e:
                logger.warning(f"Token refresh failed: {e}")
                return None

        return None

    @staticmethod
    def _run_oauth_flow(credentials_path: str) -> Credentials:
        """Run the OAuth 2.0 installed-app flow; tries browser then console."""
        with open(credentials_path, "r") as f:
            client_config = json.load(f)
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        try:
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed via local browser.")
        except Exception as e:
            logger.warning(f"Browser OAuth failed ({e}), falling back to console.")
            with open(credentials_path, "r") as f:
                client_config = json.load(f)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_console()
            logger.info("OAuth flow completed via console.")
        return creds

    @staticmethod
    def _write_token(creds: Credentials, token_file: str) -> None:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())


# --------------------------------------------------------------------------- #
#  Module-level singleton                                                      #
# --------------------------------------------------------------------------- #

_manager: Optional[MultiAccountManager] = None


def get_account_manager() -> MultiAccountManager:
    """Return (or lazily create) the global MultiAccountManager instance."""
    global _manager
    if _manager is None:
        _manager = MultiAccountManager()
    return _manager
