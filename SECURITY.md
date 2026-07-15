# Security notes

[日本語](#日本語) | [English](#english)

---

## 日本語

このリポジトリはprivateでの運用を想定していますが、シークレットとメッセージ本文、さらに活動量メタデータ(どのルームが存在するか・いつ何件動いたか)まで含めて、git履歴やCIログに一切残らない設計にしています。将来の公開範囲変更やコラボレーター追加といった設定ミスがあっても被害が広がらないよう、多層防御としています。

- **Chatworkの内容はこのリポジトリに含まれません。** メッセージ・ファイルは直接Google Driveへアップロードされ、gitには一切コミットされません。
- **差分管理用の状態(`state.json`)もgitではなくGoogle Drive側に保存。** ルームID・メッセージID・ファイルIDのリスト(本文は含まない)ですが、これすら公開リポジトリの履歴には残さない方針です。
- **実行ログはルームを特定できない集計値のみ。** 「合計で何件のメッセージ・ファイルが新規に取得されたか」だけを出力し、`room_id`やルーム名、ルームごとの内訳は一切出力しません。
- **Driveの権限は最小限。** `drive.file` スコープを使用しており、アプリ自身が作成したファイル/フォルダにしかアクセスできません(ユーザーのDrive全体にはアクセスできません)。トークンが漏洩しても無関係なファイルは読めません。
- **認証情報はGitHub Actions Secretsにのみ存在します。** コードや設定ファイルには一切含めません: `CHATWORK_API_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`。
- **`scripts/get_refresh_token.py` はローカル専用ツールです。** ブラウザでの対話的なOAuth同意フローを実行するため、CI上では絶対に実行しないでください。
- ChatworkのAPIトークンやGoogleのrefresh tokenが万一漏洩した場合は、直ちにローテーションしてください(Chatwork: アカウント設定でトークンを再発行 / Google: https://myaccount.google.com/permissions でアクセスを取り消してから `get_refresh_token.py` を再実行)。

---

## English

This repo is meant to be run as **private**, but secrets, message content,
and even activity metadata (which rooms exist, how much traffic they see)
are kept out of git history and CI logs entirely — defense in depth in
case visibility or collaborator settings are ever misconfigured.

- **No Chatwork content in this repo.** Messages and files are uploaded
  directly to Google Drive and never committed to git.
- **Incremental state (`state.json`) lives on Google Drive, not git.** It
  only holds room/message/file IDs (no content), but even that is kept out
  of the repo's history.
- **Run logs are aggregate-only.** Only combined totals ("N new messages,
  M new files across all rooms") are printed — no room id, room name, or
  per-room breakdown.
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
