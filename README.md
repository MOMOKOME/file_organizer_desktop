# File Organizer v3 — Product Edition / Phase 3A Simple

## Simple UI

対象フォルダ → 整理方法・除外 → 整理予定プレビュー → 確認して整理 → 結果 → 履歴・元に戻す、の順に操作します。
移動予定・除外・予定作成時の問題は既存APIの実データです。未提供のスキップ件数は表示しません。
一覧はスクロールでき、長いパスでもレイアウトが崩れません。処理中は設定・重複実行を無効化します。
進捗の通信に失敗した場合は「処理状況を再確認」で同じ処理の状況だけを読み直せます。
Simpleのみを実装し、外部CDN・Webフォント・オンラインアセットはありません。
見た目の調整手順と機能保護事項は [UI_DESIGN_HANDOFF.md](UI_DESIGN_HANDOFF.md) を参照してください。

開発用の実ブラウザUIテストは任意依存として分離しています。既存Microsoft Edgeを使用します。

```powershell
python -m pip install -r requirements-ui-test.txt
python -m pytest tests -q -o pythonpath=.
```

Playwright未導入の場合はUIテストだけskipされます。全UI確認時は上記依存を導入してください。
検証画像は `.verification-simple/` に保存されます。配布物にはテストツールを含めません。

## Windows配布版

`File Organizer` フォルダ全体を展開し、`File Organizer.exe` をダブルクリックしてください。
専用ウィンドウが開きます。Python、pip、コマンド入力、外部ブラウザは不要です。
`_internal` を含む配布フォルダ全体が必要です。exeだけを取り出さないでください。
対応環境はWindows 10/11 x64、.NET Framework 4.8、Microsoft Edge WebView2 Runtimeです。
WebView2がない場合はMicrosoftの公式Runtimeを導入してください。

右上の×で終了します。整理・Undo中は処理完了と履歴保存を待ちます。
大きな処理中は終了に時間がかかります。強制終了を避け、最初はコピーした一時フォルダで試してください。
ユーザーデータは `%LOCALAPPDATA%\MOMONGA_Lab\FileOrganizer\` に保存します。
`state.sqlite3` は履歴・設定、`desktop.log` は技術ログ、`desktop.lock` は多重起動防止用です。
終了後に配布フォルダを削除すればアンインストールできます。
履歴・設定も削除するには、終了後にユーザーデータフォルダを削除してください。
履歴を削除するとUndoできなくなります。整理済みファイル自体は削除されません。
旧版の `.organizer_data/state.sqlite3` は自動移行しません。引き継ぐ場合は両アプリを終了し、
旧DBをバックアップして上記保存先へコピーしてください。

## デスクトップ開発・配布ビルド

開発者のみPythonが必要です。`file_organizer` ディレクトリで実行します。

```powershell
python -m pip install -r requirements-build.txt
python desktop_app.py
python -m pytest tests -q -o pythonpath=.
.\build_windows.bat
```

`build_windows.bat` は `.venv-build` を作り、依存インストール、全テスト、PyInstallerビルドを順に実行します。
成功/失敗を表示し、失敗時は停止します。Python実行ファイルは `FILE_ORGANIZER_BUILD_PYTHON` で指定できます。
自動実行では `build_windows.bat --no-pause` を使用します。既存環境で同等のビルドを行うコマンドは次です。

```powershell
python -m PyInstaller --noconfirm --clean FileOrganizer.spec
```

成果物は `dist/File Organizer/File Organizer.exe`。`dist/File Organizer` 全体を配布してください。
onedir方式、`console=False`、UPX無効。Pythonランタイム、SQLite、Flask、pywebviewのDLL、
`templates/`、`static/` を含みます。リソースは開発時のモジュール位置または `_MEIPASS` から解決します。
任意の `icons/app.ico` を配置して再ビルドすればexeとウィンドウのアイコンへ反映されます。
アイコン未配置でも標準アイコンでビルドできます。アプリ名・ブランド・バージョンは `app_config.py` に集約しています。
依存は `requirements.txt`（Web/CLI）、`requirements-desktop.txt`（専用ウィンドウ）、
`requirements-build.txt`（ビルド・テスト）に分かれています。

Werkzeugサーバーは `127.0.0.1:0` に直接バインドし、OSが割り当てた空きポートを
pywebview/EdgeChromiumで表示します。終了時はHTTP受付を止め、実行中リクエストと整理ワーカーを待ちます。
同じデータ保存先ではOSのファイルロックでデスクトップの多重起動を拒否します。
クラッシュ時もOSがロックを解放します。ロックファイルは削除不要です。
開発Web/CLIはこの起動ロックの対象外なので、デスクトップと同時実行しないでください。
`LocalState(directory)` / `create_app(data_directory=...)` で開発・テストの保存先を指定できます。

Windows実機確認は `tests/test_desktop_exe.ps1`。一時保存先で生成exeのウィンドウ・UI・
localhost・整理/Undo・多重起動・正常終了を確認します。

A local Windows file organizer with preview, background progress, safe collision handling, two organization rules, extension exclusions, saved settings, history and confirmed Undo. Files, filenames and history stay on this PC; no accounts, external APIs or network services are used.

## 開発用Web / CLI起動（従来互換）

Requires Python 3.10+ and Flask as listed in `requirements.txt`. If dependencies are missing, install them explicitly in your chosen environment:

```powershell
python -m pip install -r requirements.txt
python web_app.py
```

Run these commands from `file_organizer`. Open `http://127.0.0.1:5000`. The server binds only to `127.0.0.1`, with debug mode disabled. Use `--no-browser` to avoid opening a browser or `--port 8000` to change the port. Keep the console open while working; stop with Ctrl+C after an operation finishes.

The existing `start_web.bat` launcher is also available. Its existing behavior installs missing Flask dependencies automatically, so use the Python command above if you want to manage dependencies yourself. The existing CLI remains available with `python file_organizer.py`.

## Use

1. Choose a folder using the native Windows picker, or enter its path.
2. Choose the organization rule and enter excluded extensions separated by commas, for example `.exe, .zip, .tmp`. Case and an omitted leading dot are normalized.
3. Save settings, or create a preview (which also saves the selected options).
4. Review original filenames, destination folders/paths, target count and excluded count. Creating a preview does not move files.
5. Start and confirm. The existing progress and result panels show successes and individual failures.
6. View recent execution history below the results, or refresh it. Use the Undo button for the latest execution, review the source/destination list, then confirm.

Only files directly inside the selected folder with an extension are organized. Subfolders, extensionless files and symbolic links are skipped. Existing destination names receive `_1`, `_2`, etc. If a destination appears after preview, the file fails safely instead of overwriting it. Files changed after preview require a new preview.

## Rules

- `extension`: the existing behavior, for example `photo.JPG` becomes `jpg/photo.JPG`. The filename is preserved; the extension folder is lowercase.
- `type`: common image, video, audio, document and archive extensions go into the Japanese category folders shown by the UI. Unknown extensions go into the Other category. The full mapping is in `organization_rules.py`.

Excluded extensions are omitted from the move preview and execution, and their count is displayed separately. Options belong to the saved preview; changing controls invalidates the displayed preview.

## Undo and safety

Undo restores successfully moved files from the latest Web or CLI execution, including after restarting the application. Every Undo requires confirmation. An occupied original path is never overwritten or renamed automatically. Missing, replaced or modified destination files fail conservatively; other safe files continue. Failures are recorded in history, and the remaining files can be retried after resolving conflicts. Files already restored are not retried. Empty category folders remain in place.

A local write-ahead journal records original/destination paths, execution ID and time before each move. File identity and modification metadata are used for conservative Undo checks; file contents are not stored in history. A storage failure stops further work. Unexpected worker failures mark the execution as interrupted when storage is available, preserving pending journal entries for safe Undo recovery. Interrupted executions can leave pending entries; after restart, Undo checks the actual file identity before attempting restoration. This is not a backup or a guarantee against hardware failure. Avoid changing the target folder during execution and run one application instance at a time.

On Windows, the same-volume rename rejects existing destinations atomically. On other systems, an exclusive hard link followed by unlink is used; unsupported filesystems fail without copying over another file. The application does not remove empty folders or existing user files to resolve conflicts.

## History and settings

Local state is stored in `%LOCALAPPDATA%/MOMONGA_Lab/FileOrganizer/state.sqlite3` using Python's standard SQLite library. The distribution directory need not be writable. Settings restore the last rule and exclusion list; history retains execution time, folder, rule, ID, success/failure totals, move metadata and Undo attempts. The UI shows the latest 50 runs. The state directory is excluded from organization and ignored by Git. Do not edit the database while the application runs. Back it up if you need to retain history when moving the application.

History and Undo cover Web and CLI executions through the shared service. The CLI restores the saved rule and exclusions; explicit service arguments override those settings. With no saved settings, it uses extension organization and no exclusions. The existing low-level core functions remain usable independently without persistence. The core functions default to the original extension rule; `create_organization_plan(folder, rule="type", excluded_extensions=[".exe"])` provides the new options.

## Local API

- `GET /api/settings`, `POST /api/settings`: read/save `rule` (`extension` or `type`) and `excluded_extensions` (a list).
- `POST /api/preview`: `folder`, optional `rule` and `excluded_extensions`; returns the existing preview fields plus options and `excluded_count`.
- `POST /api/jobs`, `GET /api/jobs/<job_id>`: existing background execution and progress API.
- `GET /api/history`: most recent 50 execution records, newest first.
- `GET /api/history/<run_id>/undo-preview`: latest run's remaining restoration paths.
- `POST /api/history/<run_id>/undo`: requires `{ "confirmed": true }` and returns success/failure counts and per-file failures.

Invalid inputs return 400, missing records 404, duplicate/busy/ineligible operations 409, and storage errors 503. A file-level failure is reported in results without preventing other safe moves. Technical exceptions are logged rather than shown as a traceback in the UI.

## Tests

From the `target_project` directory, with pytest already installed:

```powershell
python -m pytest
```

`pytest.ini` selects this application's tests and supplies its import path. Tests use temporary files and isolated state, and cover the original behavior, both rules, exclusions, collisions, changed files, partial Undo, restart persistence, settings validation, API errors, storage failures, CLI settings restoration and file changes between Undo validation and execution. Existing unittest regression tests can also be run from `file_organizer` with `python -m unittest discover -s tests -v` (pytest is required only for the new tests).

The existing manual Windows checks remain in `tests/test_start_web.ps1` and `tests/test_windows_browser_flow.ps1`. They launch native windows and are separate from the Python test suite.
