"""Run this locally (never in CI) to obtain a Google OAuth refresh_token.

Usage:
    pip install google-auth-oauthlib
    python scripts/get_refresh_token.py <client_id> <client_secret>

Opens a browser for consent, then prints the refresh_token to store as the
GOOGLE_REFRESH_TOKEN GitHub secret. The client_id/client_secret come from a
Google Cloud OAuth client of type "Desktop app".
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> None:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <client_id> <client_secret>", file=sys.stderr)
        raise SystemExit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]

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
