# chatwork-backup

Periodically backs up Chatwork messages and files — including 1-on-1 DMs,
which the Chatwork API exposes as rooms with `type: "direct"` — to Google
Drive via a scheduled GitHub Actions workflow (see
`.github/workflows/backup.yml`, default: daily 07:00 JST).

See `SECURITY.md` for the security model (no message content is ever
committed to this repo; only Google Drive holds actual content).

## Setup

### 1. Chatwork API token

Get your personal API token from Chatwork: **My profile → API token**.

### 2. Google OAuth client

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select
   a project and enable the **Google Drive API**.
2. Create an OAuth client of type **Desktop app** under
   *APIs & Services → Credentials*. Note the client ID and client secret.
3. Locally (not in CI):
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_refresh_token.py <client_id> <client_secret>
   ```
   This opens a browser for consent and prints a `refresh_token`.

### 3. Register GitHub secrets

```bash
gh secret set CHATWORK_API_TOKEN
gh secret set GOOGLE_CLIENT_ID
gh secret set GOOGLE_CLIENT_SECRET
gh secret set GOOGLE_REFRESH_TOKEN
```

### 4. Run

The workflow runs on the schedule above, or trigger manually:

```bash
gh workflow run backup.yml
```

On first run, a `ChatworkBackup` folder is created in the Drive account
that authorized the OAuth client, with one subfolder per room/DM.

## Local development

```bash
pip install -r requirements.txt
cd src
CHATWORK_API_TOKEN=... GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... python main.py
```
