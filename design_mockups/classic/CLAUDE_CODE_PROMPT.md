# Claude Code へ渡すプロンプト（Classic Edition）

VS Code で `file_organizer` フォルダを開いた状態で、下の「---」以下をそのまま貼り付けてください。

---

CLAUDE.md を前提に作業してください。

今回のタスク: File Organizer に、GUIだけが異なる追加商品「Classic Edition」を作る。
整理機能・安全機構・API・データは Simple と完全に同じで、見た目と画面構成（サイドバー付き）だけが違う。
Simple（現行の Workspace 版）は標準版として、挙動も見た目も一切変えない。

## まず読むもの

- design_mockups/classic/CLASSIC_HANDOFF.md（今回の仕様。最優先で読む）
- design_mockups/classic/screenshots/ の4枚（初期 / プレビュー後 / 整理完了後 / 履歴。見た目の正解）
- design_mockups/classic/classic_mock.css と classic_botanical.css、botanical/*.svg
- UI_DESIGN_HANDOFF.md（JSが依存するID・API契約）
- templates/index.html, static/style.css, static/app.js, web_app.py, app_config.py, desktop_app.py, FileOrganizer.spec, build_windows.bat
- tests/（特に test_simple_ui.py, test_desktop.py）

## 注意（現在のリポジトリ状態）

- git status で13ファイルが変更扱いになっているが、`git diff --ignore-cr-at-eol` では差分がない（改行コードCRLFの違いだけ）。
  これらのファイルの改行コードを一括で変換したり、内容を書き直したりしないこと。今回のタスクと無関係な差分を増やさないこと。
- commit / push はしないこと。

## 進め方

最初は実装せず、実装計画だけを出して止まってください。計画には次を含めてください。

1. 版（simple / classic）の切り替え方式
   - app_config.py での版の定義、開発時の切り替え方、配布ビルドでの埋め込み方
   - Simple の既存挙動・既存テスト・既存ビルドに影響しない根拠
2. 追加・変更するファイルの一覧
   - 例: templates/classic/index.html、static/classic/classic.css、static/classic/classic.js、static/classic/botanical/*.svg、Classic 用ビルド設定、tests/test_classic_ui.py
   - web_app.py の変更はテンプレート選択（と表示名の受け渡し）だけに限ること
3. Classic のテンプレートが UI_DESIGN_HANDOFF.md の ID・属性・dialog・ARIA をすべて同じ形で持てる根拠
4. サイドバーの画面切替（整理する / 履歴 / ヘルプ）の仕組みと、エラー表示・処理中・Undo との関係
5. 「作成されるフォルダー」一覧と件数を、API を変えずに出す方法（推奨: classic.js が描画済みの表を読んで集計）
6. static/app.js を変更する必要があるか（ある場合は最小の変更内容と理由）
7. 植物装飾の実装方法（推奨: botanical/*.svg を mask-image として使い、色トークンで着色）
8. ウィンドウタイトル・exe名・配布フォルダ名（File Organizer Classic）と、データ保存先・多重起動ロックを Simple と共有する点の扱い
9. テスト計画（既存テスト＋Classic 用UIテスト、1100×800 / 800×600、exe 実機確認）
10. 判断が必要な点・リスク

計画を私が確認してから実装に進みます。
実装後は CLAUDE.md の報告フォーマットで報告し、作業報告を docs/work_log/ に Markdown で保存してください（Cowork 側の Claude がファイルを直接読んで確認します）。
