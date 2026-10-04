# design_mockups

採用済みの GUI 刷新案「Workspace（構造A × 視認性B × 質感C）」のモックと引き継ぎ資料です。
**アプリ本体のコードではありません。** PyInstaller の配布物にも含まれません（spec は `templates/` と `static/` だけを同梱します）。

## まず読むもの

1. `WORKSPACE_HANDOFF.md` — デザイン判断、レイアウト、px値・色、実装時の制約
2. `screenshots/` — 3状態の 1100×800 画像（見た目の正解）

## モックの見方（3状態）

`workspace_initial.html` を Edge などのブラウザで開き、上部のリンクで切り替えます。

| 状態 | ファイル | スクリーンショット |
| --- | --- | --- |
| 1. 初期画面 | `workspace_initial.html` | `screenshots/workspace_initial_1100x800.png` |
| 2. プレビュー後 | `workspace_preview.html` | `screenshots/workspace_preview_1100x800.png` |
| 3. 整理完了後 | `workspace_done.html` | `screenshots/workspace_done_1100x800.png` |

- 3ファイルとも `workspace_mock.css`（共通のモックCSS）を読み込みます。`mock_viewer.css` は台紙（中央寄せと切替リンク）だけです。
- 静的なモックなので、ボタンを押しても動きません。外部への通信もありません。
- `source/` は Cowork のキャンバスで表示した原本（Design Component 形式）です。ブラウザ単体では表示できません。参照用です。
- スクリーンショットは Linux で撮影したため、日本語フォントが Windows（Yu Gothic UI）と少し違って見えます。
