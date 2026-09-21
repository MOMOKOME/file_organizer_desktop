"""Windowsのフォルダ選択ダイアログを専用プロセスで表示する。

FlaskのリクエストスレッドからTkinterを直接起動すると、Windows環境によっては
ダイアログが前面に出ずリクエストが待機したままになる。そのため、このファイルを
独立したPythonプロセスのメインスレッドとして実行する。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def choose_folder() -> str | None:
    """最前面のネイティブダイアログでフォルダを1つ選択する。"""

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.title("File Organizer Folder Picker")
    root.geometry("1x1+0+0")
    root.overrideredirect(True)
    root.attributes("-alpha", 0.0)
    root.attributes("-topmost", True)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update_idletasks()
    root.update()

    initial_directory = os.environ.get("FILE_ORGANIZER_PICKER_INITIAL_DIR")
    if initial_directory and not Path(initial_directory).is_dir():
        initial_directory = None

    try:
        selected = filedialog.askdirectory(
            parent=root,
            title="整理するフォルダを選択してください",
            initialdir=initial_directory,
            mustexist=True,
        )
        return selected or None
    finally:
        root.destroy()


def main() -> int:
    try:
        folder = choose_folder()
        # ASCIIだけで出力し、Windowsのコードページ差による破損を避ける。
        print(json.dumps({"folder": folder}, ensure_ascii=True), flush=True)
        return 0
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
