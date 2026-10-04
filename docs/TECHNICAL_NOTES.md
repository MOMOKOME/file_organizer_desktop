# File Organizer — Technical Notes

README から移した、開発者向けの詳細資料です。UI を変更する場合は先に [UI_DESIGN_HANDOFF.md](../UI_DESIGN_HANDOFF.md) を読んでください。

## Desktop app internals

- `desktop_app.py` は Werkzeug サーバーを `127.0.0.1:0` に直接バインドし、OS が割り当てた空きポートを pywebview（EdgeChromium / WebView2）で表示します。
- 終了時は HTTP の受付を止め、実行中のリクエストと整理ワーカーの完了を待ってからウィンドウを閉じます。
- 同じデータ保存先では、OS のファイルロックでデスクトップ版の多重起動を拒否します。クラッシュ時も OS がロックを解放するため、ロックファイルの削除は不要です。
- 開発用の Web / CLI 起動はこの起動ロックの対象外です。デスクトップ版と同時に実行しないでください。
- 初期ウィンドウは 1100×800 を目標にし、カーソルがあるモニターの作業領域（タスクバーを除く）より大きい場合は縮小して中央に表示します。pywebview 6 はプロセスをシステム DPI 対応にして、指定サイズに `GetDpiForWindow()/96` を掛けるため、作業領域も同じ座標系（システム DPI 対応スレッド）で取得し、システム DPI で割って論理 px に変換しています。取得できない場合は従来どおり 1100×800 の中央表示です。
- `LocalState(directory)` / `create_app(data_directory=...)` で、開発・テスト時の保存先を指定できます。
- アプリ名・ブランド・バージョンは `app_config.py` に集約しています。

## Windows build details

- `build_windows.bat` は `.venv-build` を作り、依存のインストール、全テスト、PyInstaller ビルドを順に実行します。成功/失敗を表示し、失敗時は停止します。Python 実行ファイルは `FILE_ORGANIZER_BUILD_PYTHON` で指定できます。自動実行では `build_windows.bat --no-pause` を使用します。
- 成果物は `dist/File Organizer/File Organizer.exe` です。`_internal` を含む `dist/File Organizer` フォルダ全体を配布します。
- onedir 方式、`console=False`、UPX 無効。Python ランタイム、SQLite、Flask、pywebview の DLL、`templates/`、`static/` を含みます。リソースは開発時のモジュール位置、または `_MEIPASS` から解決します。
- `FileOrganizer.spec` は、pywebview のビルド用フック（`webview.__pyinstaller`）と、実行時に使わないビルドツール（PyInstaller 本体・setuptools など）を配布物から除外しています。PyInstaller 本体のビルド用モジュールは GPL で、ブートローダー例外の対象外のためです。除外を外すと、`THIRD_PARTY_NOTICES.md` の前提が変わります。
- `python tools/make_release_zip.py` は、利用条件・プライバシー・第三者ライセンスの文書を exe の隣に配置し、`dist/release-<版>/` に配布 ZIP と `SHA256SUMS.txt` を作ります。
- `icons/app.ico` を配置して再ビルドすると、exe とウィンドウのアイコンに反映されます。未配置でも標準アイコンでビルドできます。
- 依存は `requirements.txt`（Web/CLI）、`requirements-desktop.txt`（専用ウィンドウ）、`requirements-build.txt`（ビルド・テスト）、`requirements-ui-test.txt`（任意の UI テスト）に分かれています。

## User data and uninstall

- ユーザーデータは `%LOCALAPPDATA%\MOMONGA_Lab\FileOrganizer\` に保存します。`state.sqlite3` は履歴・設定、`desktop.log` は技術ログ、`desktop.lock` は多重起動防止用です。
- 終了後に配布フォルダを削除すればアンインストールできます。履歴・設定も削除するには、終了後にユーザーデータフォルダを削除してください。履歴を削除すると Undo できなくなります。整理済みファイル自体は削除されません。
- 旧版の `.organizer_data/state.sqlite3` は自動移行しません。引き継ぐ場合は両アプリを終了し、旧 DB をバックアップしてから上記の保存先へコピーしてください。

## Use

1. Choose a folder using the native Windows picker, or enter its path.
2. Choose the organization rule and enter excluded extensions separated by commas, for example `.exe, .zip, .tmp`. Case and an omitted leading dot are normalized.
3. Save settings, or create a preview (which also saves the selected options).
4. Review original filenames, destination folders/paths, target count and excluded count. Creating a preview does not move files.
5. Start and confirm. The progress and result panels show successes and individual failures.
6. View recent execution history, or refresh it. Use the Undo button for the latest execution, review the source/destination list, then confirm.

Only files directly inside the selected folder with an extension are organized. Subfolders, extensionless files and symbolic links are skipped. Existing destination names receive `_1`, `_2`, etc. If a destination appears after preview, the file fails safely instead of overwriting it. Files changed after preview require a new preview.

## Rules

- `extension`: for example `photo.JPG` becomes `jpg/photo.JPG`. The filename is preserved; the extension folder is lowercase.
- `type`: common image, video, audio, document and archive extensions go into the Japanese category folders shown by the UI. Unknown extensions go into the Other category. The full mapping is in `organization_rules.py`.

Excluded extensions are omitted from the move preview and execution, and their count is displayed separately. Options belong to the saved preview; changing controls invalidates the displayed preview.

## Undo and safety

Undo restores successfully moved files from the latest Web or CLI execution, including after restarting the application. Every Undo requires confirmation. An occupied original path is never overwritten or renamed automatically. Missing, replaced or modified destination files fail conservatively; other safe files continue. Failures are recorded in history, and the remaining files can be retried after resolving conflicts. Files already restored are not retried. Empty category folders remain in place.

A local write-ahead journal records original/destination paths, execution ID and time before each move. File identity and modification metadata are used for conservative Undo checks; file contents are not stored in history. A storage failure stops further work. Unexpected worker failures mark the execution as interrupted when storage is available, preserving pending journal entries for safe Undo recovery. Interrupted executions can leave pending entries; after restart, Undo checks the actual file identity before attempting restoration. This is not a backup or a guarantee against hardware failure. Avoid changing the target folder during execution and run one application instance at a time.

On Windows, the same-volume rename rejects existing destinations atomically. On other systems, an exclusive hard link followed by unlink is used; unsupported filesystems fail without copying over another file. The application does not remove empty folders or existing user files to resolve conflicts.

## History and settings

Local state is stored in `%LOCALAPPDATA%/MOMONGA_Lab/FileOrganizer/state.sqlite3` using Python's standard SQLite library. The distribution directory need not be writable. Settings restore the last rule and exclusion list; history retains execution time, folder, rule, ID, success/failure totals, move metadata and Undo attempts. The UI shows the latest 50 runs. The state directory is excluded from organization and ignored by Git. Do not edit the database while the application runs. Back it up if you need to retain history when moving the application.

History and Undo cover Web and CLI executions through the shared service. The CLI restores the saved rule and exclusions; explicit service arguments override those settings. With no saved settings, it uses extension organization and no exclusions. The low-level core functions remain usable independently without persistence. The core functions default to the extension rule; `create_organization_plan(folder, rule="type", excluded_extensions=[".exe"])` provides the other options.

## Local API

- `GET /api/settings`, `POST /api/settings`: read/save `rule` (`extension` or `type`) and `excluded_extensions` (a list).
- `POST /api/preview`: `folder`, optional `rule` and `excluded_extensions`; returns the preview fields plus options and `excluded_count`.
- `POST /api/jobs`, `GET /api/jobs/<job_id>`: background execution and progress API. Execution accepts only the server-issued `preview_id`.
- `GET /api/history`: most recent 50 execution records, newest first.
- `GET /api/history/<run_id>/undo-preview`: latest run's remaining restoration paths.
- `POST /api/history/<run_id>/undo`: requires `{ "confirmed": true }` and returns success/failure counts and per-file failures.

Invalid inputs return 400, missing records 404, duplicate/busy/ineligible operations 409, and storage errors 503. A file-level failure is reported in results without preventing other safe moves. Technical exceptions are logged rather than shown as a traceback in the UI.

## Development Web / CLI (legacy-compatible)

Run these commands from the repository root:

```powershell
python -m pip install -r requirements.txt
python web_app.py
```

Open `http://127.0.0.1:5000`. The server binds only to `127.0.0.1`, with debug mode disabled. Use `--no-browser` to avoid opening a browser or `--port 8000` to change the port. Keep the console open while working; stop with Ctrl+C after an operation finishes.

`start_web.bat` is also available; it installs missing Flask dependencies automatically, so use the Python command above if you want to manage dependencies yourself. The CLI remains available with `python file_organizer.py`.

## Tests

From the repository root:

```powershell
python -m pip install -r requirements-build.txt      # pytest
python -m pip install -r requirements-ui-test.txt    # optional: Playwright UI tests (uses installed Microsoft Edge)
python -m pytest tests -q -o pythonpath=.
node --check static/app.js
```

Tests use temporary files and isolated state. They cover both rules, exclusions, collisions, changed files, partial Undo, restart persistence, settings validation, API errors, storage failures, CLI settings restoration, file changes between Undo validation and execution, the desktop launcher (instance lock, localhost binding, shutdown draining, window sizing) and, when Playwright is installed, the real UI flow in Edge. Without Playwright only the UI tests are skipped. UI review images are written to `.verification-simple/` (ignored by Git).

The unittest regression tests can also be run with `python -m unittest discover -s tests -v`.

Windows checks that launch native windows are separate from the Python test suite:

- `tests/test_desktop_exe.ps1`: launches the built exe with a temporary LOCALAPPDATA and checks the window, UI, localhost binding, preview/organize/Undo, duplicate-instance rejection and normal shutdown.
- `tests/test_start_web.ps1`, `tests/test_windows_browser_flow.ps1`: legacy Web launcher checks.
