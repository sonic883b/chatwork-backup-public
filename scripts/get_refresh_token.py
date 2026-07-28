"""Run this locally (never in CI) to obtain a Google OAuth refresh_token.

Usage:
    pip install google-auth-oauthlib
    GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... python scripts/get_refresh_token.py
    # or, if the env vars aren't set, you'll be prompted interactively.

Opens a browser for consent, then prints the refresh_token to store as the
GOOGLE_REFRESH_TOKEN GitHub secret. The client_id/client_secret come from a
Google Cloud OAuth client of type "Desktop app".

client_secret is deliberately not accepted as a CLI argument, since that
would leave it recoverable in shell history and process listings.
"""
import os
import sys
from getpass import getpass

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> None:
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or input("Google OAuth client_id: ").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or getpass("Google OAuth client_secret: ")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # access_type=offline + prompt=consent force Google to issue a
    # refresh_token even if this client previously granted consent -
    # without them a rerun can silently come back with refresh_token=None.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        print("\nNo refresh_token returned - revoke access at "
              "https://myaccount.google.com/permissions and try again.", file=sys.stderr)
        raise SystemExit(1)

    print("\nSave this as the GOOGLE_REFRESH_TOKEN secret:\n")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
