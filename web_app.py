"""file_organizer のローカルWebアプリ入口。"""

from __future__ import annotations

import argparse
import os
import webbrowser
from threading import Timer
from typing import Callable, Optional

from flask import Flask, jsonify, render_template, request

from organizer_service import (
    JobManager,
    PreviewStore,
    job_to_dict,
    preview_to_dict,
    select_folder_native,
)


def create_app(
    preview_store: Optional[PreviewStore] = None,
    job_manager: Optional[JobManager] = None,
    folder_picker: Optional[Callable[[], Optional[str]]] = None,
) -> Flask:
    """テストや将来の別UIからも利用できるFlaskアプリを作成する。"""

    app = Flask(__name__)
    app.json.ensure_ascii = False

    previews = preview_store or PreviewStore()
    jobs = job_manager or JobManager()
    pick_folder = folder_picker or select_folder_native

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/select-folder")
    def select_folder():
        try:
            folder = pick_folder()
            return jsonify({"cancelled": folder is None, "folder": folder})
        except Exception as error:
            app.logger.exception("Windowsフォルダ選択の呼び出しに失敗しました")
            return jsonify({"error": f"フォルダ選択を開けませんでした: {error}"}), 500

    @app.post("/api/preview")
    def create_preview():
        payload = request.get_json(silent=True) or {}
        folder = str(payload.get("folder", "")).strip()
        if not folder:
            return jsonify({"error": "整理するフォルダを選択してください。"}), 400

        try:
            preview = previews.create(folder)
            return jsonify(preview_to_dict(preview))
        except (OSError, RuntimeError, ValueError) as error:
            return jsonify({"error": f"整理予定を作成できませんでした: {error}"}), 400

    @app.post("/api/jobs")
    def start_job():
        payload = request.get_json(silent=True) or {}
        preview_id = str(payload.get("preview_id", "")).strip()
        if not preview_id:
            return jsonify({"error": "整理予定が指定されていません。"}), 400

        preview = previews.get(preview_id)
        if preview is None:
            return jsonify({"error": "整理予定が見つかりません。もう一度プレビューしてください。"}), 404
        if not preview.plan_result.plans:
            return jsonify({"error": "整理対象のファイルがありません。"}), 400

        try:
            job = jobs.start(preview)
            return jsonify(job_to_dict(job)), 202
        except ValueError as error:
            return jsonify({"error": str(error)}), 409

    @app.get("/api/jobs/<job_id>")
    def get_job(job_id: str):
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "処理状況が見つかりません。"}), 404
        return jsonify(job_to_dict(job))

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="file_organizer Webアプリ")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")))
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="起動時にブラウザを自動で開かない",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = f"http://127.0.0.1:{args.port}"

    print("=" * 60)
    print("File Organizer Web を起動します")
    print(f"ブラウザで {url} を開いてください")
    print("終了するには、この画面で Ctrl+C を押してください")
    print("=" * 60)

    if not args.no_browser:
        Timer(1.0, lambda: webbrowser.open(url)).start()

    create_app().run(
        host="127.0.0.1",
        port=args.port,
        debug=False,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
