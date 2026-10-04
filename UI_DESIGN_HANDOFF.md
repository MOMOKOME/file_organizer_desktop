# File Organizer — Simple UI / Phase 3A 引き継ぎ

このプロジェクトを直接改修したSimple版です。Cyber / Calm / Momo、テーマ切替UI、マスコットは未実装です。
デザイン調整時も、ファイル操作の確認・履歴・Undo・安全な状態管理を維持してください。

## UI全体構成

1. ヘッダー: File Organizer、短い説明、控えめなブランド・バージョン。
2. 操作手順と現在の案内、必要時のエラーバナー。
3. 対象フォルダ（選択ボタンと編集可能なパス）。
4. 整理方法（ネイティブradioカード）と説明。
5. 任意の除外拡張子、常時表示の入力例、設定保存。
6. プレビュー（移動予定・除外・予定作成時の問題、スクロール可能な一覧）。
7. 確認ダイアログを経た整理実行、実データによる進捗。
8. 成功・失敗の件数と理由、次の操作。
9. 最新50件の履歴カード、直前の整理のUndo予定と確認、復元結果。

プレビューの合計対象数・拡張子なし/サブフォルダ等のスキップ数はAPIにないため表示しません。
`failure_count`はフォルダ自体のエラーも含むため「予定作成時の問題」と表記します。
整理結果の記録数は成功+失敗です（事前検出した失敗を含み、実移動件数とは異なります）。

## ファイルとCSS構造

- `templates/index.html`: Jinjaテンプレート。外部CDNなし、線画アイコンはinline SVG。
- `static/style.css`: 1.design tokens / 2.base / 3.layout / 4.components / 5.states / 6.responsive。
- `static/app.js`: Vanilla JavaScript。API、描画、確認、ポーリング、処理状態。
- `web_app.py`: ヘッダーのbrand/versionをapp_configから渡すだけ。API・整理ロジックは維持。
- `app_config.py`: ブランド・バージョンの唯一の定義。表示用にテンプレートへ渡します。

フォントはSegoe UI / Yu Gothic UI / Meiryoのローカルスタック。Webフォント不要。
コンテンツ最大幅960px、主要ウィンドウ1100×800、最小800×600。
一覧には高さ上限とキーボードスクロール可能な領域があります。パスは折り返し、入力欄は横スクロール。

## Design token一覧（style.css冒頭）

| 分類 | トークン |
| --- | --- |
| 背景 | `--color-bg`, `--color-surface`, `--color-surface-muted` |
| 文字・境界 | `--color-text`, `--color-text-secondary`, `--color-border` |
| 1系統のアクセント | `--color-accent`, `--color-accent-hover`, `--color-accent-soft`, `--color-on-accent` |
| 意味を持つ状態色 | `--color-success`, `--color-success-soft`, `--color-warning`, `--color-warning-soft`, `--color-danger`, `--color-danger-soft` |
| フォーカス・ダイアログ | `--color-focus`, `--color-backdrop` |
| 角丸 | `--radius-sm`, `--radius-md`, `--radius-lg` |
| 影 | `--shadow-sm`, `--shadow-md` |
| 余白 | `--space-xs`, `--space-sm`, `--space-md`, `--space-lg`, `--space-xl` |
| 文字 | `--font-ui`, `--text-sm`, `--text-base` |
| 幅・動き | `--content-width`, `--motion-fast` |

装飾色・半透明色もトークン内で定義。HTMLに色を埋め込まないでください。
success/warning/dangerは結果の意味に限定し、主要CTAはアクセントの青です。
状態を色だけで示さず、文字・チェック/注意記号・disabledを併用します。
hover等は180ms。prefers-reduced-motion時はCSS transitionとJSのsmooth scrollを無効化します。

## JavaScriptとの接続: ID・属性を保持する

以下のIDを削除・重複・変更しないでください。

| 範囲 | 主なID/属性 |
| --- | --- |
| フォルダ | `folderPath`, `selectFolderButton`, `previewButton` |
| 設定 | `organizationRule`（fieldset）, `name="organizationRule"`（radio）, `value="extension"` / `value="type"`, `excludedExtensions`, `saveSettings`, `settingsStatus` |
| プレビュー | `previewSection`, `previewEmpty`, `previewContent`, `previewBadge`（strong子要素必須）, `previewRows`（tbody）, `planCount`, `excludedCount`, `previewFailureCount`, `previewFailures`, `previewFailureList`, `previewNotice`, `previewNoticeText`, `organizeButton` |
| 進捗 | `progressSection`, `progressStatus`, `currentFile`, `progressPercent`, `progressBar`, `.progress-track`, `progressCount`, `retryProgress` |
| 結果 | `resultSection`, `resultIcon`, `resultHeading`, `resultDescription`, `successCount`, `failureCount`, `processedCount`, `successResults`, `failureResults`, `successRows`, `failureRows`, `startOverButton` |
| 履歴 | `historyRows`（div）, `historyEmpty`, `refreshHistory`, `undoLatest`, `undoAvailability`, `undoResult` |
| エラー | `errorBanner`, `errorMessage`, `closeError`, `appStatus` |
| 確認 | `confirmDialog`, `confirmCount`, `confirmStartButton`, `undoDialog`, `undoFiles`, `undoCount` |
| 手順 | `.step`, `data-step="1/2/3"`, `is-active`, `is-done`, `aria-current` |

`previewRows` / `successRows` / `failureRows`はtableのtbodyです。
`historyRows`はカード用divへ変更済み。tableへ戻すにはJSのカード描画も変更が必要です。
`organizationRule`をselectへ戻す場合はreadOptions、設定復元、disabled制御を同時変更する必要があります。
radioはfieldsetによる一括disabledとネイティブ矢印キー操作を利用しています。

## API接続と変更してはいけない挙動

| 操作 | 既存API・payload |
| --- | --- |
| フォルダ選択 | `POST /api/select-folder`, `{}`。cancelledなら現在の選択を保持 |
| 設定 | `GET /api/settings`, `POST /api/settings`。`rule`, `excluded_extensions`（配列） |
| プレビュー | `POST /api/preview`。`folder`, `rule`, `excluded_extensions` |
| 整理実行 | `POST /api/jobs`。サーバー発行`preview_id`のみを渡す |
| 進捗 | `GET /api/jobs/<job_id>`。350ms間隔、バックエンドのprogress/processed/totalのみ使用 |
| 履歴 | `GET /api/history`。最新のrunだけがUndo対象 |
| 復元予定 | `GET /api/history/<run_id>/undo-preview`。サーバーの一覧を表示 |
| Undo実行 | `POST /api/history/<run_id>/undo`。`{confirmed:true}`は確認後にだけ送信 |

- `state`のfolder/preview/jobId/polling/operationBusy/undoEligibleを保持してください。
  phaseはidle/folder-selected/preview-ready/running/completed/errorを示す表示用状態です。
- フォルダ・ルール・除外を変更したらプレビューを失効させます。
- 作成中は対象設定をロックし、古いレスポンスの別フォルダへの適用を防ぎます。
- 処理中は設定・開始・Undoを無効化し、JSのguardとサーバー側の重複防止を維持します。
- ポーリングの通信失敗では処理終了とみなさずロックを維持します。
  「処理状況を再確認」は同じjobを読み直すだけで、整理を再送信しません。
- 整理/Undoともカスタムdialogの確認が必要。form method=dialogを維持。
  整理実行のreturnValueは`default`、Undoは`undo`、取消は`cancel`です。
- ファイル名・パス・エラー・履歴をtextContentで描画してください。innerHTMLへ文字列を入れないでください。
- API URL、payload、バックグラウンド処理、SQLite、ジャーナル、同名保護、確認後の移動を変更しないでください。
- `desktop_app.py`、多重起動ロック、127.0.0.1限定、正常終了、PyInstaller spec、LOCALAPPDATAはUI調整対象外。

## Theme-ready構造と安全に変更できる範囲

rootは`<html lang="ja" data-theme="simple">`。
`:root, [data-theme="simple"]`にトークンを定義し、コンポーネントはvar()で参照します。
将来のテーマは別のdata-themeセレクターでトークンを上書きできますが、今回はSimpleのみです。
テーマ切替、他テーマ、マスコット、オンラインアセットを追加しないでください。

Manusはトークン値・余白・文字サイズ・境界・角丸・SVG・静的な補足文を安全に調整できます。
ID/属性/hidden/dialog/button type/label関連/role/ARIA/fieldset構造は維持してください。
装飾目的でdisabledを解除したり、確認を省略したり、ファイルパスを省略して確認不能にしないでください。
CSSの色を調整したら文字コントラストを確認し、focus-visibleとreduced-motionを残してください。

## 変更後の検証

```powershell
python -m pip install -r requirements-ui-test.txt
python -m pytest tests -q -o pythonpath=.
node --check static/app.js
python -m PyInstaller --noconfirm --clean FileOrganizer.spec
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_desktop_exe.ps1
```

PlaywrightのUIテストは開発用で、既存Microsoft Edgeを使用します。
Playwright未導入ならUIテストだけskip。全機能確認時はrequirements-ui-testを導入してください。
新規UIテストは一時ファイルのみを使い、外部リクエストとJS例外がないことも検査します。
画面確認用画像は`.verification-simple/`に生成します。実機確認記録は`.verification-desktop/`です。
