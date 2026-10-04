# Phase 2 実装・検証結果

検証日: 2026-10-02、Windows 11 x64 (10.0.26200)。Git commit / pushは実施していません。

## 追加・変更

- 追加: `app_config.py`, `desktop_app.py`, `FileOrganizer.spec`, `build_windows.bat`
- 追加: `requirements-desktop.txt`, `requirements-build.txt`, `icons/README.md`, `.gitignore`
- 追加: `tests/test_desktop.py`, `tests/test_desktop_exe.ps1`, 本報告書
- 変更: `local_state.py`（既定データ保存先）, `web_app.py`（リソースパスのみ）,
  `organizer_service.py`（非daemonワーカーと完了待機）, `README.md`
- 既存整理コア・ルール・Web API・CLI・HTML/CSS/JS・既存テストは維持。

## 起動・配布

`desktop_app.py` → Werkzeug/Flask (127.0.0.1のOS割当ポート) → pywebview/EdgeChromium。
外部ブラウザを起動しません。Windowsネイティブフォルダダイアログはpywebviewから呼び出します。
PyInstaller onedir、console=False、UPX無効。Pythonランタイム、SQLite、Flask、
pywebview/Windows DLL、templates/staticを同梱。任意のicons/app.icoも同梱できます。
成果物: `dist/File Organizer/File Organizer.exe`。同フォルダ全体を配布します。
PEヘッダーSubsystem=2 (Windows GUI)を確認し、コンソール版ではないことを検証しました。
依存Windowsコンポーネント: .NET Framework 4.8、Microsoft Edge WebView2 Runtime。

## 保存・安全な終了

既定DB: `%LOCALAPPDATA%\MOMONGA_Lab\FileOrganizer\state.sqlite3`。
配布ディレクトリには保存しません。明示的な開発/テスト保存先指定を維持。
×ボタンは終了ワーカーを開始し、GUIのメッセージループを維持しながらHTTP受付停止、
実行中リクエスト（Undoを含む）と整理ワーカーの履歴保存完了を待ち、ウィンドウを破棄します。
同じ保存先のdesktop.lockのOSロックで多重起動を拒否。クラッシュ時はOSがロックを解放。
開発用Web/CLIはデスクトップ起動ロックの対象外なので同時実行しないでください。

## 自動テスト

アプリ: **46 passed**（既存34件 + 新規12件）。
パイプライン本体: **49 passed, 1 skipped**（既存のskip）。
新規テスト: 開発/凍結リソース、LOCALAPPDATA、明示DB保存先、同プロセス/別プロセスの多重起動拒否、
HTTP/静的UI配信、localhost限定、動的ポートと既存listener共存、終了の冪等性、
実行中操作/HTTPリクエストの終了待機、ランチャー正常/失敗時の後処理、
一時ファイルのプレビュー→整理→履歴→Undo。

実行コマンド（開発仮想環境を使用）:

```text
python -m pip install -r requirements-build.txt
python -m pytest tests -q -o pythonpath=.
python -m PyInstaller --noconfirm --clean FileOrganizer.spec
```

build_windows.bat相当の依存確認・テスト・PyInstaller処理を実際に実行。
Python 3.14.7 / PyInstaller 6.22.3 / pywebview 6.2.1 / Flask 3.1.3。
ビルド成功・dist生成済み。非Windowsバックエンド用の未導入モジュール警告はありますが、
Windows exeの起動・UI表示・ファイル操作は通っています。

## 生成exeの実機確認

`tests/test_desktop_exe.ps1` の最終実行は成功。
記録: `.verification-desktop/fc6bf8695bfa4699b47738fee1880b25/result.json`。
この検証ではLOCALAPPDATAを一時ディレクトリへ置き換え、ユーザーファイルは使用していません。

- 専用ウィンドウ `File Organizer 3.2.0` を検出。
- UIAutomationで専用ウィンドウ内のHTML、入力欄、整理予定ボタン、履歴を検出。
- HTML/CSS/JavaScript、設定・履歴APIの読込成功。起動直後のクラッシュなし。
- listenerは `127.0.0.1:55451` の1件のみ。
- 生成exeのAPI経由で一時ファイルのプレビュー・整理・履歴・Undoを実行、内容一致。
- LOCALAPPDATAのDB生成成功。
- 2個目のexeは「すでに起動」の警告を表示し、処理サーバーを起動せず終了。
- CloseMainWindow（×と同じWM_CLOSE）による正常終了、終了コード0。
- exeとWebView2子プロセスを含む7プロセスの残存数0。

## 未実施確認・残る制約

- Python未導入の別PC/クリーンVMでの起動は未実施。同梱ランタイム構成と生成exe起動は確認済み。
- 全ボタンのGUIクリック操作、フォルダ選択ダイアログの操作、処理中の×操作の実機試験は未実施。
  UI描画は実機、整理/Undoは生成exe API、処理待機は自動テストで確認。
- 黒いコンソールの有無の目視確認は未実施。PEのWindows GUI subsystemと専用ウィンドウ起動を確認。
- 正式アイコンは未提供のため標準アイコン。任意icoを配置して再ビルド可能。
- 旧DBの自動移行なし（READMEに終了・バックアップ・手動コピー手順）。
- WebView2/.NETがない環境の導入は別途必要。高度なインストーラーは今回の対象外。
- 停電・OS強制終了・ストレージ故障では安全終了を保証できません。既存の移動前ジャーナルは維持。

要求された実装・全アプリテストPASS・実ビルド・dist生成・生成exe起動/終了は完了。
