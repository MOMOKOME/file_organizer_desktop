# design_mockups/classic

追加GUI商品「File Organizer Classic」（大人向け・落ち着いたGUI）の確定デザインと引き継ぎ資料です。
**アプリ本体のコードではありません。** 配布物にも含めません。

## まず読むもの

1. `CLASSIC_HANDOFF.md` — デザイン判断・レイアウト・色・推奨アーキテクチャ・実装時の制約
2. `screenshots/` — 4画面の 1100×800 画像（見た目の正解）
3. `CLAUDE_CODE_PROMPT.md` — Claude Code に渡す最初のプロンプト

## モックの見方

`classic_initial.html` を Edge で開き、上部のリンクで4画面を切り替えます。

| 状態 | ファイル | スクリーンショット |
| --- | --- | --- |
| 1. 整理する（初期） | `classic_initial.html` | `screenshots/classic_initial_1100x800.png` |
| 2. プレビュー後 | `classic_preview.html` | `screenshots/classic_preview_1100x800.png` |
| 3. 整理完了後 | `classic_done.html` | `screenshots/classic_done_1100x800.png` |
| 4. 履歴と元に戻す | `classic_history.html` | `screenshots/classic_history_1100x800.png` |

- 静的なモックなので、ボタンを押しても動きません。外部への通信もありません。
- `botanical/` は植物装飾の原本SVG（本番で使う素材）、`generator/` はそれを作った Python スクリプトです。
- `source/` は Cowork キャンバスで確定した原本（参照用）です。
