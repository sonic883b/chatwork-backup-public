# chatwork-backup

[日本語](#日本語) | [English](#english)

---

## 日本語

Chatworkのメッセージ・ファイルを定期的にGoogle Driveへバックアップします。1対1のDM(Chatwork APIでは `type: "direct"` のルームとして扱われる)も含めて、アクセス可能な全ルームが対象です。GitHub Actionsのスケジュール実行(`.github/workflows/backup.yml`、デフォルトは毎日07:00 JST)で動きます。

セキュリティ設計については `SECURITY.md` を参照してください(メッセージ本文はこのリポジトリに一切コミットされず、実データはGoogle Driveにのみ保存されます)。

### セットアップ

#### 1. Chatwork APIトークン

Chatworkの **マイプロフィール → API Token** から個人用APIトークンを取得します。

#### 2. Google OAuthクライアント

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成(または選択)し、**Google Drive API** を有効化します。
2. *APIs & Services → Credentials* で **デスクトップアプリ** 種別のOAuthクライアントを作成し、クライアントIDとクライアントシークレットを控えます。
3. ローカル環境で(CI上では実行しないこと):
   ```bash
   pip install google-auth-oauthlib
   export GOOGLE_CLIENT_ID=...
   export GOOGLE_CLIENT_SECRET=...
   python scripts/get_refresh_token.py
   ```
   環境変数を設定しない場合は対話的に入力を求められます(`client_secret` はシェル履歴に残らないよう非表示入力になります)。ブラウザが開いて同意画面が表示され、完了すると `refresh_token` が出力されます。

#### 3. GitHub Secretsの登録

```bash
gh secret set CHATWORK_API_TOKEN
gh secret set GOOGLE_CLIENT_ID
gh secret set GOOGLE_CLIENT_SECRET
gh secret set GOOGLE_REFRESH_TOKEN
```

#### 4. 実行

上記のスケジュールで自動実行されますが、手動でもトリガーできます。

```bash
gh workflow run backup.yml
```

初回実行時、OAuthクライアントを認可したGoogleアカウントのDrive上に `ChatworkBackup` フォルダが作成され、ルーム/DMごとにサブフォルダが作られます。

### ローカル開発

```bash
pip install -r requirements.txt
cd src
CHATWORK_API_TOKEN=... GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... python main.py
```

### 既知の制約

Chatwork APIの仕様上、メッセージ・ファイルとも1回のリクエストで取得できるのは最新100件までで、それより古い履歴をページングして取得する手段は公開APIには存在しません。2回のバックアップ実行の間に101件以上の新着があった場合、古いものが欠落する可能性があります(実行ログに警告を出力します)。バックアップの実行頻度を上げることで軽減できます。

---

## English

Periodically backs up Chatwork messages and files — including 1-on-1 DMs,
which the Chatwork API exposes as rooms with `type: "direct"` — to Google
Drive via a scheduled GitHub Actions workflow (see
`.github/workflows/backup.yml`, default: daily 07:00 JST).

See `SECURITY.md` for the security model (no message content is ever
committed to this repo; only Google Drive holds actual content).

### Setup

#### 1. Chatwork API token

Get your personal API token from Chatwork: **My profile → API token**.

#### 2. Google OAuth client

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select
   a project and enable the **Google Drive API**.
2. Create an OAuth client of type **Desktop app** under
   *APIs & Services → Credentials*. Note the client ID and client secret.
3. Locally (not in CI):
   ```bash
   pip install google-auth-oauthlib
   export GOOGLE_CLIENT_ID=...
   export GOOGLE_CLIENT_SECRET=...
   python scripts/get_refresh_token.py
   ```
   If the env vars aren't set, you'll be prompted interactively instead
   (`client_secret` input is hidden so it never lands in shell history).
   This opens a browser for consent and prints a `refresh_token`.

#### 3. Register GitHub secrets

```bash
gh secret set CHATWORK_API_TOKEN
gh secret set GOOGLE_CLIENT_ID
gh secret set GOOGLE_CLIENT_SECRET
gh secret set GOOGLE_REFRESH_TOKEN
```

#### 4. Run

The workflow runs on the schedule above, or trigger manually:

```bash
gh workflow run backup.yml
```

On first run, a `ChatworkBackup` folder is created in the Drive account
that authorized the OAuth client, with one subfolder per room/DM.

### Local development

```bash
pip install -r requirements.txt
cd src
CHATWORK_API_TOKEN=... GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... python main.py
```

### Known limitation

Both the messages and files endpoints of the Chatwork API only return the
latest 100 items per request, with no pagination to reach older history.
If more than 100 new messages or files arrive between two backup runs, the
excess older ones may be skipped (a warning is printed to the run log).
Running backups more frequently mitigates this.
