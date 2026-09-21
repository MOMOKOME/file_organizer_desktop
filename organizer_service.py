"""Web UI と既存のファイル整理ロジックを接続するサービス層。

既存の ``organizer.py`` は変更せず、このモジュールがプレビューの保持、
バックグラウンド実行、進捗の集計、JSON向けデータ変換を担当する。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from typing import Callable, Dict, Optional
from uuid import uuid4

from organizer import (
    FileFailure,
    OrganizationPlan,
    OrganizationResult,
    PlanResult,
    create_organization_plan,
    execute_organization_plan,
)


@dataclass(frozen=True)
class StoredPreview:
    """画面で確認済みの整理予定。"""

    preview_id: str
    folder: Path
    plan_result: PlanResult


class PreviewStore:
    """実行時に改ざんされていない整理予定を使うためのメモリ内ストア。"""

    def __init__(self) -> None:
        self._previews: Dict[str, StoredPreview] = {}
        self._lock = Lock()

    def create(self, folder: str) -> StoredPreview:
        normalized_folder = Path(folder).expanduser().resolve()
        preview = StoredPreview(
            preview_id=uuid4().hex,
            folder=normalized_folder,
            plan_result=create_organization_plan(normalized_folder),
        )
        with self._lock:
            self._previews[preview.preview_id] = preview
        return preview

    def get(self, preview_id: str) -> Optional[StoredPreview]:
        with self._lock:
            return self._previews.get(preview_id)


@dataclass
class JobRecord:
    """バックグラウンド整理処理の現在状態。"""

    job_id: str
    preview_id: str
    folder: Path
    total: int
    status: str = "queued"
    processed: int = 0
    current_file: Optional[str] = None
    result: OrganizationResult = field(default_factory=OrganizationResult)
    error: Optional[str] = None


class JobManager:
    """既存の実行関数を1ファイルずつ呼び、進捗を記録する。"""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._started_previews: set[str] = set()
        self._lock = Lock()

    def start(self, preview: StoredPreview) -> JobRecord:
        with self._lock:
            if preview.preview_id in self._started_previews:
                raise ValueError("この整理予定はすでに実行されています。もう一度プレビューしてください。")

            job = JobRecord(
                job_id=uuid4().hex,
                preview_id=preview.preview_id,
                folder=preview.folder,
                total=len(preview.plan_result.plans),
                result=OrganizationResult(
                    failed_files=list(preview.plan_result.failures)
                ),
            )
            self._jobs[job.job_id] = job
            self._started_previews.add(preview.preview_id)

        worker = Thread(
            target=self._run,
            args=(job.job_id, preview.plan_result),
            name=f"organizer-job-{job.job_id[:8]}",
            daemon=True,
        )
        worker.start()
        return job

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job_id: str, plan_result: PlanResult) -> None:
        self._update(job_id, status="running")

        try:
            for plan in plan_result.plans:
                self._update(job_id, current_file=plan.source.name)

                # 既存のコア実行関数をそのまま利用する。
                # 1件ずつ渡すことで、コアを変更せず進捗を表示できる。
                one_result = execute_organization_plan(PlanResult(plans=[plan]))

                with self._lock:
                    job = self._jobs[job_id]
                    job.result.successful_files.extend(one_result.successful_files)
                    job.result.failed_files.extend(one_result.failed_files)
                    job.processed += 1

            self._update(job_id, status="completed", current_file=None)
        except Exception as error:  # 最終防御。詳細は画面に表示する。
            self._update(job_id, status="failed", current_file=None, error=str(error))

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for name, value in changes.items():
                setattr(job, name, value)


def select_folder_native() -> Optional[str]:
    """専用GUIプロセスを使い、Windows上でフォルダ選択を前面表示する。"""

    picker_script = Path(__file__).with_name("folder_picker.py")
    if not picker_script.is_file():
        raise RuntimeError("folder_picker.py が見つかりません。")

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    try:
        completed = subprocess.run(
            [sys.executable, str(picker_script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            creationflags=creation_flags,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"フォルダ選択プロセスを開始できませんでした: {error}") from error

    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not output_lines:
        detail = completed.stderr.strip() or "フォルダ選択プロセスから応答がありません。"
        raise RuntimeError(detail)

    try:
        payload = json.loads(output_lines[-1])
    except json.JSONDecodeError as error:
        raise RuntimeError("フォルダ選択プロセスの応答を読み取れませんでした。") from error

    if completed.returncode != 0 or payload.get("error"):
        raise RuntimeError(payload.get("error") or completed.stderr.strip())

    folder = payload.get("folder")
    return str(folder) if folder else None


def plan_to_dict(plan: OrganizationPlan, folder: Path) -> dict:
    """整理予定をUI向けの辞書へ変換する。"""

    return {
        "source_name": plan.source.name,
        "source_path": str(plan.source),
        "extension": plan.extension,
        "destination_folder": plan.destination.parent.name,
        "destination_name": plan.destination.name,
        "destination_path": str(plan.destination),
        "destination_relative": _relative_display(plan.destination, folder),
    }


def failure_to_dict(failure: FileFailure, folder: Path) -> dict:
    """失敗情報をUI向けの辞書へ変換する。"""

    return {
        "source": _relative_display(failure.source, folder) if failure.source else "対象フォルダ",
        "destination": (
            _relative_display(failure.destination, folder)
            if failure.destination
            else None
        ),
        "message": failure.message,
    }


def preview_to_dict(preview: StoredPreview) -> dict:
    """保存済みプレビューをAPIレスポンスへ変換する。"""

    return {
        "preview_id": preview.preview_id,
        "folder": str(preview.folder),
        "plan_count": len(preview.plan_result.plans),
        "failure_count": len(preview.plan_result.failures),
        "plans": [
            plan_to_dict(plan, preview.folder) for plan in preview.plan_result.plans
        ],
        "failures": [
            failure_to_dict(failure, preview.folder)
            for failure in preview.plan_result.failures
        ],
    }


def job_to_dict(job: JobRecord) -> dict:
    """ジョブ状態をAPIレスポンスへ変換する。"""

    progress = 100 if job.status == "completed" else 0
    if job.total:
        progress = round(job.processed / job.total * 100)

    return {
        "job_id": job.job_id,
        "preview_id": job.preview_id,
        "folder": str(job.folder),
        "status": job.status,
        "total": job.total,
        "processed": job.processed,
        "progress": progress,
        "current_file": job.current_file,
        "error": job.error,
        "success_count": job.result.success_count,
        "failure_count": job.result.failure_count,
        "successful_files": [
            plan_to_dict(plan, job.folder) for plan in job.result.successful_files
        ],
        "failed_files": [
            failure_to_dict(failure, job.folder)
            for failure in job.result.failed_files
        ],
    }


def _relative_display(path: Path, folder: Path) -> str:
    """対象フォルダ配下なら短い相対パス、配下でなければ絶対パスを返す。"""

    try:
        return str(path.relative_to(folder))
    except ValueError:
        return str(path)
