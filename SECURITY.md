# Security notes

This repository is public, so the design deliberately keeps secrets and
message content out of git history entirely.

- **No Chatwork content in this repo.** Messages and files are uploaded
  directly to Google Drive; only `data/state.json` (message/file IDs, no
  content) is committed back by CI.
- **Minimal Drive scope.** The app uses `drive.file`, which only grants
  access to files/folders the app itself creates — not the user's whole
  Drive. A leaked token cannot read unrelated files.
- **Credentials live in GitHub Actions secrets only**, never in code or
  config files: `CHATWORK_API_TOKEN`, `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
- **`scripts/get_refresh_token.py` is a local-only tool.** It runs an
  interactive OAuth consent flow in a browser and must never be run in CI.
- If the Chatwork API token or Google refresh token are ever exposed,
  rotate them immediately (Chatwork: regenerate token in account settings;
  Google: revoke access at https://myaccount.google.com/permissions and
  re-run `get_refresh_token.py`).
