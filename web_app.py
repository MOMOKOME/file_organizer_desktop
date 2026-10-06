"""file_organizer のローカルWebアプリ入口。"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
import webbrowser
from threading import Timer
from typing import Callable, Optional

from flask import Flask, jsonify, render_template, request

from local_state import LocalState
from app_config import resource_path, VERSION, BRAND, EDITION, EDITIONS
from organization_rules import normalize_options

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
    data_directory=None,
    edition: Optional[str] = None,
) -> Flask:
    """テストや将来の別UIからも利用できるFlaskアプリを作成する。"""

    app = Flask(__name__, template_folder=str(resource_path("templates")),
                static_folder=str(resource_path("static")))
    app.json.ensure_ascii = False

    previews = preview_store or PreviewStore()
    jobs = job_manager or JobManager(LocalState(data_directory))
    state = jobs.state
    pick_folder = folder_picker or select_folder_native
    # Editions differ only in the screen template; every API below is shared.
    edition = edition if edition in EDITIONS else EDITION
    template = "classic/index.html" if edition == "classic" else "index.html"

    @app.get("/")
    def index():
        return render_template(template, version=VERSION, brand=BRAND, app_name=EDITIONS[edition])

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
            return jsonify({"error": "フォルダ選択を開けませんでした。フォルダパスを直接入力してください。"}), 500

    @app.post("/api/preview")
    def create_preview():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "入力内容の形式が正しくありません。"}), 400
        if not isinstance(payload.get("folder", ""), str):
            return jsonify({"error": "フォルダパスを文字列で指定してください。"}), 400
        folder = payload.get("folder", "").strip()
        if not folder:
            return jsonify({"error": "整理するフォルダを選択してください。"}), 400

        try:
            options = state.settings()
            options.update({key: payload[key] for key in ("rule", "excluded_extensions") if key in payload})
            options = normalize_options(**options)
            target = Path(folder).expanduser().resolve()
            if target == state.directory or state.directory in target.parents:
                return jsonify({"error": "履歴の保存フォルダは整理できません。"}), 400
            preview = previews.create(folder, **options)
            state.save_settings(**options)
            return jsonify(preview_to_dict(preview))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except (OSError, RuntimeError):
            return jsonify({"error": "フォルダにアクセスできません。場所と権限を確認してください。"}), 400

    @app.post("/api/jobs")
    def start_job():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "入力内容の形式が正しくありません。"}), 400
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

    @app.errorhandler(OSError)
    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.exception("Local storage operation failed")
        return jsonify({"error": "ローカルデータを読み書きできません。保存先の権限と空き容量を確認してください。"}), 503

    @app.get("/api/settings")
    def get_settings():
        return jsonify(state.settings())

    @app.post("/api/settings")
    def save_settings():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) - {"rule", "excluded_extensions"}:
            return jsonify({"error": "整理ルールと除外拡張子を正しい形式で指定してください。"}), 400
        try:
            options = state.settings()
            options.update(payload)
            return jsonify(state.save_settings(**options))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @app.get("/api/history")
    def history():
        return jsonify({"history": state.history()[:50]})

    @app.get("/api/history/<run_id>/undo-preview")
    def undo_preview(run_id):
        if state.get_run(run_id) is None:
            return jsonify({"error": "実行履歴が見つかりません。"}), 404
        try:
            return jsonify(jobs.undo_preview(run_id))
        except ValueError as error:
            return jsonify({"error": str(error)}), 409

    @app.post("/api/history/<run_id>/undo")
    def undo(run_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("confirmed") is not True:
            return jsonify({"error": "元に戻す対象を確認してから実行してください。"}), 400
        if state.get_run(run_id) is None:
            return jsonify({"error": "実行履歴が見つかりません。"}), 404
        try:
            return jsonify(jobs.undo(run_id))
        except ValueError as error:
            return jsonify({"error": str(error)}), 409

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
