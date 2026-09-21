# File Organizer Web

既存のPython版 `file_organizer.py` / `organizer.py` を変更せず、ブラウザから操作できるWindows向けローカルWebアプリを追加したものです。ファイルやフォルダの情報は外部へ送信されず、アプリを起動したPC内だけで処理されます。

## 起動方法

最も簡単な方法は、エクスプローラーで **`start_web.bat` をダブルクリック**することです。起動バッチはPython Launcher（`py -3`）を優先し、利用できない場合は `python` を使用します。必要なFlaskが未導入の場合は最初の起動時だけ自動インストールし、起動後に既定のブラウザで `http://127.0.0.1:5000` を開きます。Webアプリの使用中は表示されたコンソールを閉じないでください。終了する場合は、その画面で `Ctrl+C` を押します。

コマンドから起動する場合は、次の手順です。

```bat
cd /d <file_organizerフォルダへのパス>
python -m pip install -r requirements.txt
python web_app.py
```

ブラウザを自動で開きたくない場合は `py -3 web_app.py --no-browser`、別のポートを使う場合は `py -3 web_app.py --port 8000` を実行します。

起動できない場合は、コマンドプロンプトで次を実行するとエラーを確認できます。

```bat
cd /d <file_organizerフォルダへのパス>
call start_web.bat
```

ポート5000が別のアプリで使用中の場合は、`py -3 web_app.py --port 8000` のように別ポートを指定してください。Pythonが見つからない場合は、Python 3をインストールし、Python LauncherまたはPATHを有効にします。

画面に「Webアプリのサーバーへ接続できません」と表示された場合は、起動時のコンソールが開いていることを確認し、`start_web.bat` を再起動してからブラウザを再読み込みしてください。画面だけを直接HTMLファイルとして開くのではなく、必ず `http://127.0.0.1:5000` を使用します。

## 操作方法

1. 「フォルダ選択」を押し、Windowsの画面で整理対象フォルダを選びます。必要に応じてフォルダパスを直接貼り付けることもできます。
2. 「整理予定を見る」を押し、ファイル名・拡張子・移動先を確認します。
3. 「整理開始」を押し、確認画面でもう一度「整理を開始する」を押します。
4. 進捗表示の後、成功・失敗件数と各ファイルの結果を確認します。

対象は選択フォルダ直下にある拡張子付きファイルだけです。サブフォルダ内と拡張子なしのファイルは対象外です。拡張子別フォルダ名は小文字になり、同名の移動先がある場合は `_1`、`_2` のような番号が付きます。

## 構成

| ファイル | 役割 |
| --- | --- |
| `file_organizer.py` | 既存CLI入口（無変更） |
| `organizer.py` | 既存の整理コアロジック（無変更） |
| `organizer_service.py` | プレビュー保持、バックグラウンド処理、進捗集計 |
| `folder_picker.py` | Windowsフォルダ選択を専用GUIプロセスで安全に表示 |
| `web_app.py` | Flask画面・API・Web版起動処理 |
| `templates/index.html` | Web画面 |
| `static/style.css` | 画面デザイン |
| `static/app.js` | フォルダ選択、プレビュー、確認、進捗、結果表示 |
| `tests/` | コア仕様の回帰テストとWeb APIテスト |
| `start_web.bat` | Windows向け簡単起動 |

Web UIは `organizer_service.py` を介し、既存の `create_organization_plan()` と `execute_organization_plan()` を直接利用します。1ファイルごとに既存実行関数へ渡すことで、整理ロジックを複製せず進捗を表示しています。この分離により、将来のデスクトップUIからもサービス層とコアロジックを再利用できます。

## テスト方法

```bat
py -3 -m unittest discover -s tests -v
```

`start_web.bat` 自体の起動とHTTP応答を確認する場合は、PowerShellで次を実行します。テスト終了後、検証用サーバーは自動停止します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_start_web.ps1
```

Windows版Edgeで「フォルダ選択」ボタン、実際のダイアログ、選択結果、プレビュー表示まで確認する場合は、次を実行します。テスト専用のEdgeウィンドウと検証フォルダは終了時に自動で閉じられます。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_windows_browser_flow.ps1
```

テストでは、`jpg` / `JPG` / `pdf` / `txt` / 拡張子なし / サブフォルダ / 移動先の同名ファイルを含む一時フォルダを実際に作成し、プレビューとファイル移動を確認します。また、1件で失敗が起きても他のファイルを処理できること、既存の `organize_folder()` が引き続き使えること、Web APIから非同期実行と結果取得ができることを確認します。
