# CLAUDE.md — MOMONGA Lab / File Organizer

このファイルは Claude Code が毎回読む、このプロジェクトの恒久ルールです。
このファイルだけで重要ルールが分かるように書いています。迷ったら「安全性 > 既存機能の維持 > 見た目」の順で判断してください。

---

## 1. プロジェクト概要

- 小規模開発チーム **MOMONGA Lab** による、Windows向けフォルダ整理アプリ **File Organizer** の商品化プロジェクト。
- 目標は「動くPythonツール」ではなく、**一般ユーザーが安心して使える、安全・使いやすい・見た目も完成されたWindowsアプリ**。
- 今は File Organizer の完成が最優先。別ツールや開発基盤（AI開発パイプライン等）の改良へ脱線しない。
- 現バージョン: `app_config.py` の `VERSION`（執筆時 3.2.0）。アプリ名・ブランド・バージョンは `app_config.py` が唯一の定義。

## 2. 技術構成

Python / Flask / HTML / CSS / Vanilla JavaScript / pywebview（EdgeChromium, WebView2） / PyInstaller（onedir） / SQLite（標準ライブラリ）

| ファイル | 役割 |
| --- | --- |
| `desktop_app.py` | 専用ウィンドウ起動、多重起動ロック、`127.0.0.1:0` の内部サーバー、正常終了の待機 |
| `web_app.py` | Flask アプリと Local API（`create_app`） |
| `organizer.py` | コアの整理ロジック（計画・移動・同名保護） |
| `organizer_service.py` | ジョブ管理、プレビュー、履歴、Undo、ジャーナル |
| `local_state.py` | SQLite 状態保存（設定・履歴） |
| `organization_rules.py` | 拡張子別 / ファイル種類別のルールと除外拡張子の正規化 |
| `app_config.py` | アプリ名・ブランド・バージョン・リソースパス・ユーザーデータ保存先 |
| `templates/index.html` | 画面のHTML（Jinja） |
| `static/style.css` | デザイントークンとスタイル（`data-theme="simple"`） |
| `static/app.js` | API呼び出し、描画、確認ダイアログ、ポーリング、操作ロック |
| `FileOrganizer.spec` / `build_windows.bat` | PyInstaller 配布ビルド |
| `UI_DESIGN_HANDOFF.md` | **UI変更時の必読資料**（JSが依存するID・API契約） |
| `design_mockups/` | 採用済みGUI刷新案（Workspace）のモックと引き継ぎ資料 |

- ユーザーデータ保存先: `%LOCALAPPDATA%\MOMONGA_Lab\FileOrganizer\`（`state.sqlite3` / `desktop.log` / `desktop.lock`）
- 配布物: `dist/File Organizer/` フォルダ全体（`File Organizer.exe` + `_internal`）。Python 不要。
- ウィンドウ: 1100×800、最小 800×600。

## 3. 実装済みの重要機能（壊さないこと）

フォルダ選択（Windowsダイアログ / パス直接入力）、拡張子別整理、ファイル種類別整理、除外拡張子、設定保存、
整理前プレビュー、確認ダイアログ付きの整理実行、バックグラウンド処理と進捗表示、結果表示、
実行履歴（最新50件）、直前の整理の Undo（確認ダイアログ付き）、同名ファイル保護（`_1`, `_2`…）、
サブフォルダ・拡張子なしファイル・シンボリックリンクは対象外、Preview と実行対象の整合性、
多重起動対策、正常終了時の処理完了待ち、LOCALAPPDATA 保存、localhost 限定、Windows デスクトップアプリ化、Python 不要の配布構成。

## 4. 安全ルール（最優先・弱める変更は禁止）

このアプリはユーザーの実ファイルを移動する。**便利さより安全性**。

- ファイルを削除しない。既存ファイルを上書きしない。同名時は安全な別名にする。
- Preview → 確認 → 実行 の流れ、Undo、履歴、ジャーナル、operation lock（処理中の重複操作防止）を壊さない。
- Preview と実行対象の整合性を保つ（実行は server 発行の `preview_id` のみで行う）。
- サーバーは `127.0.0.1` 限定のまま。外部サーバーへファイル・ファイル名・履歴を送らない。外部CDN・Webフォント・オンラインアセットを追加しない。
- テストに実ユーザーファイルを使わない。必ず一時ディレクトリ（pytest の `tmp_path` 等）を使う。
- 安定して動いている既存コードを「綺麗にしたいから」という理由で全面書き換えしない。

## 5. UI変更ルール

- UI を変更する前に **必ず `UI_DESIGN_HANDOFF.md` を読む**。
- JavaScript が依存する `id` / `name` / `value` / `dialog` / `form method="dialog"` / `button type` / `fieldset` / `label` 関連 / `role` / ARIA / `hidden` 属性 / `data-step` / `.step` クラス / API payload を、デザイン都合で変更・削除・重複させない。
- API URL・payload・レスポンス形式（API契約）を勝手に変更しない。
- `organizer.py` / `organizer_service.py` / `local_state.py` などのコア整理ロジックを UI 都合で変更しない。
- 文字列は `textContent` で描画する（`innerHTML` にファイル名・パス・エラーを入れない）。
- 装飾目的で `disabled` を外したり、確認ダイアログを省略したり、パスを省略して確認不能にしない。
- `focus-visible` と `prefers-reduced-motion` 対応を残す。色を変えたら文字コントラストを確認する。色だけで状態を示さない。
- テーマ構造: `<html data-theme="simple">`、トークンは `:root, [data-theme="simple"]` に定義。HTML に色を直書きしない。
- Cyber / Calm / Momo テーマ、テーマ切替UI、マスコット表示は、明示的に依頼されるまで実装しない。

## 6. Git ルール

明示的な依頼がない限り、以下は行わない:

- `git commit` / `git push`
- `git reset --hard`、`git rebase`、`git push --force` など履歴を壊す・書き換える操作
- ブランチ削除、`git clean` による未追跡ファイル削除

コード変更・テスト・ビルドまでは行ってよい。確認には `git status` / `git diff` を使う。

## 7. テスト方針

変更内容に応じて、以下を可能な範囲で実施する。

```powershell
# file_organizer ディレクトリで
python -m pip install -r requirements-ui-test.txt     # UIテスト(Playwright, 既存Edge使用)が必要な場合
python -m pytest tests -q -o pythonpath=.
node --check static/app.js
python -m PyInstaller --noconfirm --clean FileOrganizer.spec
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_desktop_exe.ps1
```

- 1つ上の `target_project` からは `python -m pytest` でも実行できる（`pytest.ini` あり）。
- UI を変えたら **1100px 前後と 800px 前後** の表示を確認する（横スクロールが出ないこと）。画面確認用画像は `.verification-simple/` に出力される。
- 実機確認項目: exe 起動 / フォルダ選択 / Preview / 整理実行 / 結果 / 履歴 / Undo / 多重起動の拒否 / 正常終了（処理中の終了で完了を待つ）。
- **「テストPASS = 要求達成」ではない。** 過去に pytest が通っても仕様が実装されていなかった例がある。作業後は次を必ず確認する:
  1. 要求された機能・見た目が本当に実装されているか
  2. 必須ファイルが存在するか
  3. テストがPASSするか
  4. 実際に起動するか / Windows アプリとして動くか
  5. 既存機能を壊していないか
- 確認できなかった項目は「未確認」と明記する。推測で完了扱いにしない。

## 8. ユーザーとの作業スタイル

- 作りながら理解できるよう、変更内容と理由を分かりやすく説明する。
- 学び方は「完成形を先に作る → 動かす → 直す → 後で仕組みを理解する」。少しずつ継ぎ足すより、まず完成版を作る。
- 説明は「例え → 仕組み → 重要ポイント」の順。図式（入力 ↓ 処理 ↓ 結果）を好む。1行ずつの長大な説明は求められた時だけ。
- 不要な確認質問で作業を止めない。安全に判断できること（コードを読む、テスト、構文チェック、一時ファイル、プロジェクト内のUI調整、PyInstaller ビルド、生成exeのテスト）は自律的に進める。
- 次は必ず事前に確認する: プロジェクト外のファイル削除、大量削除、ユーザー実データの変更、Git commit/push/履歴変更、管理者権限、Windows セキュリティ設定の変更、認証情報・APIキー、課金、外部サービスへのデータ送信、元に戻せない操作。
- 返答・報告は日本語。

## 9. AI の役割分担

- **ChatGPT**: 仕様整理、設計、アイデア、Claude へのプロンプト作成、実装レビュー、セカンドオピニオン
- **Claude Code**: コードベース理解、実装、UI/UX、テスト、Windows ビルド、検証
- **人間（ユーザー）**: 実機確認、最終判断

## 10. 作業後の報告フォーマット

まとまった作業の後は、日本語で簡潔に:
何を変更したか / 変更したファイル / なぜ / テスト結果 / ビルド結果 / 実機確認結果 / 未確認項目 / 残っている問題 / 次に人間が確認すべきこと。
技術的な失敗や制約は隠さず書く。

## 11. 進行中のタスク

- **Simple テーマの GUI 刷新（Workspace 案）**: 仕様は `design_mockups/WORKSPACE_HANDOFF.md`、見た目の正解は `design_mockups/` のモックとスクリーンショット。
- **Classic Edition（追加GUI商品）**: 仕様は `design_mockups/classic/CLASSIC_HANDOFF.md`、見た目の正解は `design_mockups/classic/screenshots/`。最初のプロンプトは `design_mockups/classic/CLAUDE_CODE_PROMPT.md`。
