# 作業報告: File Organizer Classic Edition（2026-10-06）

作業者: Claude Code（Opus 5.5）／ commit・push は未実施（指示どおり）

## 1. 何を変更したか

GUI だけが異なる追加商品「File Organizer Classic」を、Simple と同じコード（整理機能・安全機構・API・データ）の上に追加した。
Simple（標準版）のテンプレート・CSS・JS・コアロジック・既存テストは 1 バイトも変えていない（作業前後の SHA-256 で確認）。

```
起動
 ↓ app_config.EDITION を決定（exe: 同梱 edition.txt のみ / 開発時: 環境変数 FILE_ORGANIZER_EDITION / 既定 simple）
 ↓
web_app "/" → simple: templates/index.html ／ classic: templates/classic/index.html
 ↓                                   （API・整理ロジック・static/app.js は両版共通）
classic/index.html = Simple と同じ ID・属性・dialog・ARIA ＋ サイドバー・3画面・植物装飾
 ↓
classic.js: 画面切替（hidden のみ）、移動先フォルダー集計、直前の整理カード（描画済み DOM を読むだけ）
```

計画で合意した判断 A〜E はすべて推奨案で実施した。

| # | 内容 | 実施結果 |
| --- | --- | --- |
| A | Simple 配布物から Classic ファイルを除外 | `FileOrganizer.spec` の datas 1 行を、`templates/classic`・`static/classic` を除くループに置換。Simple の dist は `templates/index.html`・`static/app.js`・`static/style.css` だけ（従来と同じ） |
| B | ラベル | 「移動先フォルダー」（完了画面は「整理後のフォルダー」） |
| C | app.js | 変更なし。共通文言（「整理を実行」「フォルダ」）と完了画面の 2 列表は受け入れ |
| D | リリース ZIP | 対象外（未対応） |
| E | Classic 用 exe テスト | 別ファイル `tests/test_desktop_exe_classic.ps1` |

### データ保存先・多重起動ロックの共有（重要）

- Simple と Classic は同じ `%LOCALAPPDATA%\MOMONGA_Lab\FileOrganizer\`（`state.sqlite3` / `desktop.log` / `desktop.lock`）を使う。
  履歴・設定は両版で共通で、直前の整理はどちらの版からでも元に戻せる。
- `desktop.lock` も共有するため、**Simple と Classic は同時に起動できない**。後から起動した側は「File Organizer はすでに起動しています。」と表示して終了する。
  exe の実機テストで、Classic 起動中に Simple の exe が拒否されることを確認した。
- この内容は `design_mockups/classic/CLASSIC_HANDOFF.md` の 10.1 と、Classic のヘルプ画面にも記載した。

## 2. 変更したファイル

**変更（最小限）**
| ファイル | 内容 |
| --- | --- |
| `app_config.py` | `EDITIONS` / `EDITION_ENV` / `EDITION_MARKER` / `detect_edition()` / `EDITION` / `DISPLAY_NAME` を追加。`APP_NAME` は変更なし |
| `web_app.py` | `create_app(..., edition=None)` を追加し、`/` のテンプレート選択と `app_name` の受け渡しだけを変更（4 行）。CRLF と LF が混在しているため、触る行の改行コードをそのまま保持した |
| `desktop_app.py` | ウィンドウタイトルとエラー MessageBox のタイトルを `DISPLAY_NAME` に変更（Simple は "File Organizer" のままで同一表示） |
| `FileOrganizer.spec` | Simple 配布物から Classic ファイルを除外（判断 A） |
| `.gitignore` | `.verification-classic/` を追加 |
| `design_mockups/classic/CLASSIC_HANDOFF.md` | 「10. 実装後の確定事項」を追記（共有データ・ロック、版の切替、決定した表示） |

**新規**
| ファイル | 内容 |
| --- | --- |
| `templates/classic/index.html` | Classic 画面（サイドバー、整理する / 履歴 / ヘルプ） |
| `static/classic/classic.css` | Classic 用のスタイル。単体で完結し、`style.css` は読み込まない。トークンは `:root, [data-theme="classic"]` |
| `static/classic/classic.js` | 画面切替、移動先フォルダー集計、直前の整理カード |
| `static/classic/botanical/*.svg` | 植物装飾 4 点。C2PA の `<metadata>` と `xmlns:c2pa` だけを除去（1 枚あたり約 7.7 KB）。図形データは原本とバイト単位で同一であることを確認 |
| `FileOrganizerClassic.spec` / `build_windows_classic.bat` | Classic のビルド → `dist/File Organizer Classic/File Organizer Classic.exe` |
| `tests/test_classic_edition.py` | 版の判定、テンプレート選択、ID・属性の契約、exe と同じ構成での配信、SVG のメタデータなし（19 件） |
| `tests/test_classic_ui.py` | Edge と Playwright による Classic の UI テスト（5 件） |
| `tests/test_desktop_exe_classic.ps1` | Classic exe の実機テスト（Simple のスクリプトは変更なし） |

## 3. なぜ（主な設計判断）

- **exe は環境変数を見ない**: 利用者の環境変数で Simple の exe が Classic に化け、テンプレートがないためにクラッシュする事故を防ぐ。版は同梱の `edition.txt` だけで決まる。
- **app.js を変えずに済んだ理由**: Classic でも、app.js が参照する ID・クラスをすべて 1 個ずつ保持した。
  契約表に載っていない依存（`.folder-panel` と `.progress-track`）もテストで固定した。
  画面切替は `hidden` だけで行い、要素を消したり移動したりしないので、どの画面にいても app.js の参照は切れない。
- **エラー表示**: `#errorBanner` はどの画面の外にも出していないので、履歴画面で Undo が失敗しても見える。
- **処理中**:
  - 画面を切り替えても処理状態は壊れない。サイドバーの「整理する」に「処理中」と文字で表示する（狭い幅では点で表示）。
  - 処理中のロックは他の画面でも有効（Undo・履歴の更新は無効のまま）。
  - 完了しても勝手に画面は切り替わらない。
- **パスは省略せず折り返す**: モックは末尾を「…」で省略していたが、CLAUDE.md の「パスを省略して確認不能にしない」を優先した。
- **植物装飾**: SVG を `mask-image` にして、色トークンと不透明度で着色。`pointer-events:none` と `aria-hidden` を付け、文字より下の層に置いた。

## 4. テスト結果

- `python -m pytest tests -q -o pythonpath=.` → **86 passed**（既存 62 件はすべて変更なしで PASS、Classic 24 件を追加）。
  - 注: この環境では pytest の既定の一時フォルダー（`%TEMP%\pytest-of-<ユーザー名>`）にアクセスできず `PermissionError` になった。`--basetemp` に別の一時フォルダーを指定して実行した（コードの問題ではない）。
- `node --check static/app.js` / `static/classic/classic.js` → OK
- Classic の UI テストで確認した項目:
  - 初期表示、3画面の切替（`aria-current`、見出しへのフォーカス）
  - ファイル種類別のプレビュー → 移動先フォルダーの件数（既存のフォルダーも数える）
  - 確認ダイアログのキャンセルと実行、完了画面の「履歴」リンクから Undo
  - 履歴画面でのエラー表示、処理中の画面切替とロック
  - 外部リクエストなし、JS 例外なし
  - 1100×761 でページがスクロールしない、800×600 で横スクロールなし
  - 高さ 600 でサイドバーがスクロールしない、キーボードでの radio 操作と focus-visible、reduced-motion
- 画面確認用の画像: `.verification-classic/`（1100 と 800 の、初期・プレビュー・完了・履歴・ヘルプ）

## 5. ビルド結果

- `python -m PyInstaller --noconfirm --clean FileOrganizer.spec` → 成功。`dist/File Organizer/_internal` の中身は従来どおり（Classic のファイルは含まない）。
- `python -m PyInstaller --noconfirm --clean FileOrganizerClassic.spec` → 成功。`dist/File Organizer Classic/`（約 29 MB）。
  `_internal` には `templates/classic/`・`static/app.js`・`static/classic/`・`edition.txt` だけが入っている（Simple のテンプレートと `style.css` はなし）。
- 注: Simple を再ビルドしたため、`dist/File Organizer/` の中身は作り直された。`dist/release-3.2.0/` の ZIP と SHA256SUMS には触れていない。

## 6. 実機確認結果（PowerShell と UI Automation による自動操作）

| 項目 | Simple exe | Classic exe |
| --- | --- | --- |
| 起動・ウィンドウタイトル | File Organizer 3.2.0 | File Organizer Classic 3.2.0 |
| 127.0.0.1 限定で待ち受け | OK | OK |
| API でのプレビュー → 整理 → 履歴 → Undo | OK | OK |
| ネイティブのフォルダー選択ダイアログ | 開いて閉じる OK | 開いて閉じる OK |
| GUI でのプレビュー → 確認 → 整理 → Undo | OK | OK（完了画面の「履歴」リンクから履歴画面へ移動して Undo） |
| 同じ版の二重起動を拒否 | OK | OK |
| Classic 起動中に Simple を拒否（ロック共有） | ― | OK |
| 正常終了（終了コード 0、プロセスの残りなし） | OK | OK |

**実機で見つけて修正した問題**: この PC ではウィンドウが作業領域に合わせて約 1100×600（論理 px、150% 表示）に縮む。そのとき次の2つが起きていた。
- 游明朝の実際の文字幅で、サイドバーの「File Organizer」が2行に折り返していた。
- 植物装飾の固定高さ 768px が原因で、サイドバーにスクロールバーが出ていた。

装飾は上から切り取る方式にし、ブランド名は折り返さないようにして解消した。再ビルドした実機で確認し、UI テストにも高さ 600 の検査を追加した。

## 7. 未確認項目

- 人の目で見る実機確認（全画面の見た目を、モックのスクリーンショットと並べて見比べること）。自動テストでの撮影と、実機での履歴画面のスクリーンショットだけは確認済み。
- 処理中に×ボタンで閉じて完了を待つ動作の、Classic exe での手動確認（終了処理のコードは Simple と共通で、既存テストは PASS）。
- 一部失敗時の Classic の表示（警告色・「移動できなかったファイル」）の目視確認。CSS は作成済みで、UI テストでは成功時だけを撮影している。
- 100% 表示や 1920×1080 などの別の DPI・解像度での表示。

## 8. 残っている問題・制約

- app.js の共通文言（「整理を実行」「フォルダ」）は Classic のボタン名（「この内容で整理を実行する」）や「フォルダー」表記と完全には揃わない（判断 C で受け入れ済み）。
- 完了画面の表は 2 列（ファイル / 移動先）で、モックにあった拡張子の列はない（判断 C）。
- 多重起動を拒否するメッセージは両版とも「File Organizer はすでに起動しています。」。Classic を起動したまま Simple を起動しても同じ文言になる（Simple の挙動を変えないため変更していない）。
- ネイティブのタイトルバーの色は Windows 標準のまま（仕様で対象外）。
- 長いパスは折り返すため、モックより行が高くなることがある（安全ルールを優先）。
- `CLAUDE.md` の技術構成表には、Classic の spec・テンプレートの記載がまだない（`CLAUDE.md` は作業前から未コミットの差分があったため触れていない）。

## 9. 次に人間が確認すべきこと

1. `dist\File Organizer Classic\File Organizer Classic.exe` を起動し、4 画面（初期・プレビュー・完了・履歴）とヘルプを `design_mockups/classic/screenshots/` と見比べる。
2. ウィンドウを最小の 800×600 にしたときの表示（アイコンだけのサイドバー、縦スクロール）。
3. Simple と Classic を交互に起動して、同じ履歴が見えることと、同時に起動できないこと。
4. 問題がなければ commit の指示（今回は commit・push していない）。
5. Classic のリリース ZIP 対応（今回は対象外）を進めるかどうか。
