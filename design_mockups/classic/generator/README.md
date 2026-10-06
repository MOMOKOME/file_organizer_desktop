# generator

植物装飾（銅版画風ボタニカル）を作った Python スクリプトです。本番アプリには不要です。

- `engrave.py`: 線の強弱・葉脈・ハッチング付きの葉、実、枝、シダを SVG パスとして生成する部品。
- `compose.py`: Cowork モック（`../source/initial.dc.html` の元ファイル）に装飾を配置したスクリプト。
  枝の位置・葉の大きさ・乱数シードはここで決めています（例: `coffee_branch(...)`, `olive_branch(...)`, `fern(...)`）。

装飾を調整したい場合は、これらの値を変えて SVG を作り直し、`../botanical/*.svg` を差し替えてください。
