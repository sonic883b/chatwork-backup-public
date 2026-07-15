# chatwork-backup (portfolio / template)

[日本語](#日本語) | [English](#english)

---

## 日本語

> **これはポートフォリオ/テンプレート用の公開リポジトリです。**
> 実際の運用は別のprivateリポジトリで行っており、このrepoにはシークレット類は一切設定されていません(GitHub Actionsのスケジュール実行もコメントアウトして無効化済み)。コード自体はここに書いてある通り汎用的で、実データやルーム固有の情報は一切含みません。設計・実装の参考やフォークしてのセルフホストにどうぞ。

Chatworkのメッセージ・ファイルを定期的にGoogle Driveへバックアップする、GitHub Actions cron駆動のツールです。1対1のDM(Chatwork APIでは `type: "direct"` のルームとして扱われる)も含めて、アクセス可能な全ルームが対象です。

**設計上のポイント**
- メッセージは各ルームの `messages/` フォルダに、実行ごとに2形式(JSON生データ + 読みやすいGoogle Docトランスクリプト)で保存
- 差分管理用の状態(`state.json`)はgitではなくGoogle Drive側に保存し、リポジトリの公開範囲に関わらず「どのルームが存在するか」「いつ何件動いたか」がgit履歴やCIログに残らない設計(詳細は `SECURITY.md`)
- Google Driveへのアクセスは `drive.file` スコープのみ(アプリが作成したファイル/フォルダにしか触れない、最小権限のOAuth設計)
- Chatwork APIの制約(メッセージ・ファイルとも最新100件までしか取得できずページングなし)を踏まえた欠落検知ロジック

自分で使う場合は、このrepoをフォークまたはテンプレートとして、以下のセットアップ手順に沿ってGitHub Secretsを設定し、`.github/workflows/backup.yml` の `schedule:` のコメントアウトを外してください。

### セットアップ

#### 1. Chatwork APIトークン

Chatworkの **マイプロフィール → API Token** から個人用APIトークンを取得します。

#### 2. Google OAuthクライアント

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成(または選択)し、**Google Drive API** を有効化します。
2. *APIs & Services → Credentials* で **デスクトップアプリ** 種別のOAuthクライアントを作成し、クライアントIDとクライアントシークレットを控えます。
3. ローカル環境で(CI上では実行しないこと):
   ```bash
   pip install -r requirements.txt
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

> **This is a public portfolio/template copy.** The live deployment runs
> in a separate private repository with no secrets here, and the
> scheduled trigger below is commented out so nothing runs unattended.
> The code itself is fully generic and contains no real data or
> room-specific information — feel free to read it, fork it, or
> self-host it.

Periodically backs up Chatwork messages and files — including 1-on-1 DMs,
which the Chatwork API exposes as rooms with `type: "direct"` — to Google
Drive via a GitHub Actions cron workflow (see `.github/workflows/backup.yml`).

**Design highlights**
- Two message formats per run in each room's `messages/` folder: raw JSON
  and a human-readable Google Doc transcript
- Incremental state (`state.json`) lives on Google Drive, not git, so
  which rooms exist and how much traffic they see never touches this
  repo's history or CI logs, regardless of repo visibility (see `SECURITY.md`)
- Minimal-privilege Google OAuth: `drive.file` scope only (app-created
  files/folders, not the user's whole Drive)
- Handles the Chatwork API's hard 100-item cap (no pagination) on both
  the messages and files endpoints, with gap detection

To actually run this, fork or use as a template, set up the GitHub
secrets below, and uncomment the `schedule:` block in
`.github/workflows/backup.yml`.

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
   pip install -r requirements.txt
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
