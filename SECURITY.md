# Security notes

[日本語](#日本語) | [English](#english)

---

## 日本語

このリポジトリはpublicであるため、シークレットとメッセージ本文をgit履歴に一切残さない設計にしています。

- **Chatworkの内容はこのリポジトリに含まれません。** メッセージ・ファイルは直接Google Driveへアップロードされ、CIがコミットバックするのは `data/state.json`(メッセージ/ファイルIDのみで本文なし)だけです。
- **Driveの権限は最小限。** `drive.file` スコープを使用しており、アプリ自身が作成したファイル/フォルダにしかアクセスできません(ユーザーのDrive全体にはアクセスできません)。トークンが漏洩しても無関係なファイルは読めません。
- **認証情報はGitHub Actions Secretsにのみ存在します。** コードや設定ファイルには一切含めません: `CHATWORK_API_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`。
- **`scripts/get_refresh_token.py` はローカル専用ツールです。** ブラウザでの対話的なOAuth同意フローを実行するため、CI上では絶対に実行しないでください。
- ChatworkのAPIトークンやGoogleのrefresh tokenが万一漏洩した場合は、直ちにローテーションしてください(Chatwork: アカウント設定でトークンを再発行 / Google: https://myaccount.google.com/permissions でアクセスを取り消してから `get_refresh_token.py` を再実行)。

---

## English

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
