# icons

File Organizer 専用のアプリアイコンです。MOMONGA Lab 全体の共通ロゴではありません。

| ファイル | 内容 |
| --- | --- |
| `file_organizer_icon_source.png` | デザイン原本（1254×1254）。加工せずに保管します |
| `app.ico` | Windows アプリ用アイコン（16 / 24 / 32 / 48 / 64 / 128 / 256 px） |
| `build_icon.py` | 原本から `app.ico` を生成する開発用スクリプト |

`app.ico` は `FileOrganizer.spec` で exe のアイコンとして埋め込まれ、配布物にも同梱されます。
起動時は `desktop_app.py` が pywebview に渡し、ウィンドウ（タイトルバー・タスクバー・Alt+Tab）にも使われます。
`app.ico` がない場合も、PyInstaller の標準アイコンでビルドできます。

## app.ico の再生成

原本を差し替えた場合だけ実行します（アプリの実行・ビルドには Pillow は不要です）。

```powershell
python -m pip install -r requirements-icon.txt
python icons/build_icon.py
```

生成時に行うのは技術的な加工だけです。原本の絵柄・色は変更しません。

- 角丸タイルの外側（オフホワイトの背景と影）を透明にする
- タイルを正方形の透明キャンバスの中央に配置する（周囲に約3%の余白）
- 各サイズへ高品質に縮小し、1つの ICO にまとめる
