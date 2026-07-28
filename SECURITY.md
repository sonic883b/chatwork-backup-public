# Security notes

[日本語](#日本語) | [English](#english)

---

## 日本語

**本番運用は別のprivateリポジトリで行っており、これは秘密情報を一切含まないpublicなtemplate/portfolio用コピーです。** 実運用でこのコードを使う場合は、privateリポジトリとして運用してください。

その前提を踏まえたうえで、この設計自体はシークレットとメッセージ本文、さらに活動量メタデータ(どのルームが存在するか・いつ何件動いたか)まで含めて、git履歴やCIログに一切残さないようにしています。private運用時に公開範囲変更やコラボレーター追加といった設定ミスがあっても被害が広がらないよう、多層防御としての設計です。

- **Chatworkの内容はこのリポジトリに含まれません。** メッセージ・ファイルは直接Google Driveへアップロードされ、gitには一切コミットされません。
- **差分管理用の状態(`state.json`)もgitではなくGoogle Drive側に保存。** ルームID・メッセージID・ファイルIDのリスト(本文は含まない)ですが、これすら公開リポジトリの履歴には残さない方針です。
- **実行ログはルームを特定できない集計値のみ。** 「合計で何件のメッセージ・ファイルが新規に取得されたか」だけを出力し、`room_id`やルーム名、ルームごとの内訳は一切出力しません。
- **Driveの権限は最小限。** `drive.file` スコープを使用しています。このスコープ自体は「アプリが作成したファイル」に加えて「ユーザーがPicker等でアプリに明示的に開かせたファイル」にもアクセスできる仕様ですが、本実装はPickerを一切使わないため、実際にアクセスするのはアプリ自身が作成したファイル/フォルダのみです。いずれにせよユーザーのDrive全体にはアクセスできないため、トークンが漏洩しても無関係なファイルは読めません。
- **認証情報はGitHub Actions Secretsにのみ存在します。** コードや設定ファイルには一切含めません: `CHATWORK_API_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`。
- **`scripts/get_refresh_token.py` はローカル専用ツールです。** ブラウザでの対話的なOAuth同意フローを実行するため、CI上では絶対に実行しないでください。
- ChatworkのAPIトークンやGoogleのrefresh tokenが万一漏洩した場合は、直ちにローテーションしてください(Chatwork: アカウント設定でトークンを再発行 / Google: https://myaccount.google.com/permissions でアクセスを取り消してから `get_refresh_token.py` を再実行)。

---

## English

**Production runs in a separate private repository. This is a public
template/portfolio copy with no secrets configured.** If you deploy this
code for real use, run it as a **private** repository.

With that said, the design itself keeps secrets, message content, and even
activity metadata (which rooms exist, how much traffic they see) out of
git history and CI logs entirely — defense in depth in case a private
deployment's visibility or collaborator settings are ever misconfigured.

- **No Chatwork content in this repo.** Messages and files are uploaded
  directly to Google Drive and never committed to git.
- **Incremental state (`state.json`) lives on Google Drive, not git.** It
  only holds room/message/file IDs (no content), but even that is kept out
  of the repo's history.
- **Run logs are aggregate-only.** Only combined totals ("N new messages,
  M new files across all rooms") are printed — no room id, room name, or
  per-room breakdown.
- **Minimal Drive scope.** The app uses `drive.file`. The scope itself
  permits access to files the app creates *and* to existing files the
  user explicitly opens with the app via the Picker API — but this
  implementation never uses the Picker, so in practice it only ever
  touches files/folders it created itself. Either way it can't reach the
  user's whole Drive, so a leaked token can't read unrelated files.
- **Credentials live in GitHub Actions secrets only**, never in code or
  config files: `CHATWORK_API_TOKEN`, `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
- **`scripts/get_refresh_token.py` is a local-only tool.** It runs an
  interactive OAuth consent flow in a browser and must never be run in CI.
- If the Chatwork API token or Google refresh token are ever exposed,
  rotate them immediately (Chatwork: regenerate token in account settings;
  Google: revoke access at https://myaccount.google.com/permissions and
  re-run `get_refresh_token.py`).
