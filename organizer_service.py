"""Preview storage, background progress, local execution history and safe Undo."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable, Dict, Optional
from uuid import uuid4

from local_state import LocalState, now, file_identity
from organization_rules import normalize_options

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
    rule: str = "extension"
    excluded_extensions: tuple = ()


class PreviewStore:
    """実行時に改ざんされていない整理予定を使うためのメモリ内ストア。"""

    def __init__(self) -> None:
        self._previews: Dict[str, StoredPreview] = {}
        self._lock = Lock()

    def create(self, folder: str, rule="extension", excluded_extensions=None) -> StoredPreview:
        options = normalize_options(rule, excluded_extensions)
        normalized_folder = Path(folder).expanduser().resolve()
        preview = StoredPreview(
            preview_id=uuid4().hex,
            folder=normalized_folder,
            plan_result=create_organization_plan(normalized_folder, **options),
            rule=rule,
            excluded_extensions=tuple(options["excluded_extensions"]),
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
    finished: Event = field(default_factory=Event, repr=False)


class JobManager:
    """既存の実行関数を1ファイルずつ呼び、進捗を記録する。"""

    def __init__(self, state=None) -> None:
        self.state = state or LocalState()
        self._operation_lock = Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._started_previews: set[str] = set()
        self._lock = Lock()

    def start(self, preview: StoredPreview) -> JobRecord:
        if preview.folder == self.state.directory or self.state.directory in preview.folder.parents:
            raise ValueError("履歴の保存フォルダは整理できません。")
        if not self._operation_lock.acquire(blocking=False):
            raise ValueError("処理中です。完了するまでお待ちください。")
        with self._lock:
            if preview.preview_id in self._started_previews:
                self._operation_lock.release()
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
            daemon=False,
        )
        try:
            self.state.save_settings(preview.rule, list(preview.excluded_extensions))
            self.state.save_run({
                "run_id": job.job_id, "executed_at": now(), "folder": str(preview.folder),
                "rule": preview.rule, "excluded_extensions": list(preview.excluded_extensions),
                "success_count": 0, "failure_count": len(preview.plan_result.failures),
                "status": "running", "moves": [], "failures": [
                    failure_to_dict(f, preview.folder) for f in preview.plan_result.failures],
            })
            worker.start()
        except Exception:
            self._operation_lock.release()
            with self._lock:
                self._started_previews.discard(preview.preview_id)
                self._jobs.pop(job.job_id, None)
            raise
        return job

    def wait_for_idle(self):
        """Called after HTTP intake stops; never abandon a file move or Undo."""
        with self._operation_lock:
            pass
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            job.finished.wait()

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job_id: str, plan_result: PlanResult) -> None:
        self._update(job_id, status="running")

        try:
            run = self.state.get_run(job_id)
            for plan in plan_result.plans:
                self._update(job_id, current_file=plan.source.name)

                # 既存のコア実行関数をそのまま利用する。
                # 1件ずつ渡すことで、コアを変更せず進捗を表示できる。
                identity = list(plan.identity) if plan.identity is not None else None
                move = {"source": str(plan.source), "destination": str(plan.destination),
                        "identity": identity, "status": "pending", "executed_at": now()}
                run["moves"].append(move)
                self.state.save_run(run)  # Journal before touching the file.
                one_result = execute_organization_plan(PlanResult(plans=[plan]))
                move["status"] = "moved" if one_result.success_count else "failed"
                run["success_count"] += one_result.success_count
                run["failure_count"] += one_result.failure_count
                run["failures"].extend(failure_to_dict(f, Path(run["folder"]))
                                       for f in one_result.failed_files)
                with self._lock:
                    job = self._jobs[job_id]
                    job.result.successful_files.extend(one_result.successful_files)
                    job.result.failed_files.extend(one_result.failed_files)
                    job.processed += 1
                self.state.save_run(run)

            run["status"] = "completed"
            self.state.save_run(run)
            self._update(job_id, status="completed", current_file=None)
        except Exception:  # Log technical details; return a friendly UI message.
            logging.getLogger(__name__).exception("Organization job failed")
            # Preserve pending journal entries for recovery, but mark the run as
            # interrupted when storage is still available.
            try:
                stored_run = self.state.get_run(job_id)
                if stored_run is not None:
                    stored_run["status"] = "interrupted"
                    self.state.save_run(stored_run)
            except Exception:
                logging.getLogger(__name__).exception("Could not record interrupted run")
            self._update(job_id, status="failed", current_file=None,
                         error="処理または履歴の保存が完了しませんでした。フォルダの権限と空き容量を確認してください。")
        finally:
            self._operation_lock.release()
            self._jobs[job_id].finished.set()

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for name, value in changes.items():
                setattr(job, name, value)

    def undo_preview(self, run_id):
        history = self.state.history()
        if not history or history[0]["run_id"] != run_id:
            raise ValueError("直前の整理履歴を選んでください。")
        run = history[0]
        if run["status"] == "running" and any(
            job.status in ("queued", "running") for job in self._jobs.values()
        ):
            raise ValueError("整理が終わるまでお待ちください。")
        return {"run_id": run_id, "moves": [
            move for move in run["moves"] if move["status"] in ("moved", "pending")
        ]}

    def undo(self, run_id):
        if not self._operation_lock.acquire(blocking=False):
            raise ValueError("処理中です。完了するまでお待ちください。")
        try:
            preview = self.undo_preview(run_id)
            if not preview["moves"]:
                raise ValueError("元に戻せるファイルがありません。")
            run = self.state.get_run(run_id)
            if run["status"] == "running":
                run["status"] = "interrupted"
            result = {"run_id": run_id, "executed_at": now(),
                      "success_count": 0, "failure_count": 0, "failures": []}
            run.setdefault("undo_attempts", []).append(result)
            self.state.save_run(run)
            root = Path(run["folder"])
            for move in run["moves"]:
                if move["status"] not in ("moved", "pending"):
                    continue
                source, destination = Path(move["destination"]), Path(move["source"])
                try:
                    if (destination.parent != root or source.parent.parent != root
                            or source.is_symlink() or source.parent.is_symlink()
                            or root.resolve() != root or source.parent.resolve() != source.parent
                            or file_identity(source) != move["identity"]):
                        raise OSError("File identity or location changed")
                    one = execute_organization_plan(PlanResult(plans=[
                        OrganizationPlan(source, destination, destination.suffix.lower(),
                                         identity=tuple(move["identity"]))
                    ]))
                    if one.failed_files:
                        message = one.failed_files[0].message
                    else:
                        move["status"] = "undone"
                        result["success_count"] += 1
                        self.state.save_run(run)
                        continue
                except OSError:
                    message = "移動後のファイルが見つからないか変更されています。安全のため元に戻しませんでした。"
                result["failure_count"] += 1
                result["failures"].append({"source": str(source), "destination": str(destination),
                                           "message": message})
                self.state.save_run(run)
            return result
        finally:
            self._operation_lock.release()


def organize_with_history(folder, rule=None, excluded_extensions=None, state=None):
    """Synchronous CLI/service entry using the same journal as the Web UI."""
    manager = JobManager(state)
    options = manager.state.settings()
    if rule is not None:
        options["rule"] = rule
    if excluded_extensions is not None:
        options["excluded_extensions"] = excluded_extensions
    preview = PreviewStore().create(str(folder), **options)
    job = manager.start(preview)
    job.finished.wait()
    if job.error:
        job.result.failed_files.append(FileFailure(message=job.error, source=preview.folder))
    return job.result


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
        "rule": preview.rule,
        "excluded_extensions": list(preview.excluded_extensions),
        "excluded_count": preview.plan_result.excluded_count,
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
