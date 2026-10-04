"""v3 behavior and safety using real files and isolated local state."""

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from local_state import LocalState
from organizer import create_organization_plan, execute_organization_plan
from organizer_service import JobManager, PreviewStore, organize_with_history
from web_app import create_app


def make_files(root, *names):
    root.mkdir(exist_ok=True)
    for name in names:
        (root / name).write_text("contents:" + name, encoding="utf-8")


def finish(client, preview):
    response = client.post("/api/jobs", json={"preview_id": preview["preview_id"]})
    assert response.status_code == 202
    job = response.get_json()
    deadline = time.monotonic() + 5
    while job["status"] in ("queued", "running"):
        assert time.monotonic() < deadline
        time.sleep(0.01)
        job = client.get("/api/jobs/" + job["job_id"]).get_json()
    assert job["status"] == "completed", job
    return job


@pytest.mark.parametrize("rule,expected", [
    ("extension", {"JPG": "jpg", "mp4": "mp4", "MP3": "mp3", "pdf": "pdf",
                   "zip": "zip", "unknown": "unknown"}),
    ("type", {"JPG": "画像", "mp4": "動画", "MP3": "音声", "pdf": "文書",
              "zip": "圧縮ファイル", "unknown": "その他"}),
])
def test_rules_exclusions_and_untouched_files(tmp_path, rule, expected):
    make_files(tmp_path, *("file." + extension for extension in expected), "keep.EXE", "no_extension")
    nested = tmp_path / "nested"
    make_files(nested, "child.txt")
    plan = create_organization_plan(tmp_path, rule, ["exe", ".EXE"])
    assert plan.excluded_count == 1
    assert len(plan.plans) == len(expected)
    for item in plan.plans:
        assert item.destination.parent.name == expected[item.source.suffix[1:]]
        assert item.source.is_file()  # Preview is read-only.
    result = execute_organization_plan(plan)
    assert result.success_count == len(expected)
    assert result.failure_count == 0
    assert (tmp_path / "keep.EXE").read_text() == "contents:keep.EXE"
    assert (tmp_path / "no_extension").is_file()
    assert (nested / "child.txt").is_file()


def test_collision_created_after_preview_is_not_overwritten(tmp_path):
    make_files(tmp_path, "photo.JPG", "safe.pdf")
    plan = create_organization_plan(tmp_path, "type")
    destination = next(p.destination for p in plan.plans if p.source.suffix == ".JPG")
    destination.parent.mkdir()
    destination.write_text("existing")
    result = execute_organization_plan(plan)
    assert (result.success_count, result.failure_count) == (1, 1)
    assert destination.read_text() == "existing"
    assert (tmp_path / "photo.JPG").read_text() == "contents:photo.JPG"


def test_changed_source_after_preview_stays_put(tmp_path):
    make_files(tmp_path, "note.txt")
    plan = create_organization_plan(tmp_path)
    (tmp_path / "note.txt").write_text("replaced with different contents")
    result = execute_organization_plan(plan)
    assert result.failure_count == 1
    assert (tmp_path / "note.txt").is_file()


def test_history_settings_restart_and_undo(tmp_path):
    root, data = tmp_path / "files", tmp_path / "data"
    make_files(root, "photo.JPG", "keep.TMP")
    app = create_app(data_directory=data)
    with app.test_client() as client:
        settings = client.post("/api/settings", json={"rule": "type", "excluded_extensions": ["TMP"]})
        assert settings.status_code == 200
        assert settings.get_json() == {"rule": "type", "excluded_extensions": [".tmp"]}
        preview = client.post("/api/preview", json={"folder": str(root)}).get_json()
        assert preview["excluded_count"] == 1
        assert preview["plan_count"] == 1
        assert preview["plans"][0]["destination_folder"] == "画像"
        job = finish(client, preview)
    with create_app(data_directory=data).test_client() as client:
        assert client.get("/api/settings").get_json() == settings.get_json()
        run = client.get("/api/history").get_json()["history"][0]
        assert run["run_id"] == job["job_id"]
        assert run["executed_at"]
        assert run["folder"] == str(root.resolve())
        assert run["rule"] == "type"
        assert (run["success_count"], run["failure_count"]) == (1, 0)
        assert "contents:" not in json.dumps(run)
        url = f"/api/history/{run['run_id']}/undo"
        undo_preview = client.get(url + "-preview").get_json()
        assert len(undo_preview["moves"]) == 1
        assert client.post(url, json={}).status_code == 400
        assert not (root / "photo.JPG").exists()
        result = client.post(url, json={"confirmed": True})
        assert result.status_code == 200
        assert result.get_json()["success_count"] == 1
        assert (root / "photo.JPG").read_text() == "contents:photo.JPG"
        assert (root / "keep.TMP").is_file()
        assert client.post(url, json={"confirmed": True}).status_code == 409
        saved = client.get("/api/history").get_json()["history"][0]
        assert saved["undo_attempts"][0]["success_count"] == 1


def test_partial_undo_conflict_continues_and_can_retry(tmp_path):
    root, data = tmp_path / "files", tmp_path / "data"
    make_files(root, "a.txt", "b.pdf")
    with create_app(data_directory=data).test_client() as client:
        preview = client.post("/api/preview", json={"folder": str(root)}).get_json()
        job = finish(client, preview)
        (root / "a.txt").write_text("new user data")
        url = f"/api/history/{job['job_id']}/undo"
        result = client.post(url, json={"confirmed": True}).get_json()
        assert (result["success_count"], result["failure_count"]) == (1, 1)
        assert (root / "a.txt").read_text() == "new user data"
        assert (root / "txt" / "a.txt").read_text() == "contents:a.txt"
        assert (root / "b.pdf").read_text() == "contents:b.pdf"
        (root / "a.txt").rename(root / "preserved.txt")
        retry = client.post(url, json={"confirmed": True}).get_json()
        assert (retry["success_count"], retry["failure_count"]) == (1, 0)
        assert (root / "preserved.txt").read_text() == "new user data"
        assert len(LocalState(data).history()[0]["undo_attempts"]) == 2


@pytest.mark.parametrize("change", ["missing", "edited"])
def test_undo_does_not_restore_missing_or_modified_files(tmp_path, change):
    root = tmp_path / "files"
    make_files(root, "a.txt", "b.pdf")
    with create_app(data_directory=tmp_path / "data").test_client() as client:
        preview = client.post("/api/preview", json={"folder": str(root)}).get_json()
        job = finish(client, preview)
        moved = root / "txt" / "a.txt"
        if change == "missing":
            moved.rename(root / "manually-moved.txt")
        else:
            moved.write_text("user changed this file")
        result = client.post(f"/api/history/{job['job_id']}/undo", json={"confirmed": True}).get_json()
        assert (result["success_count"], result["failure_count"]) == (1, 1)
        assert not (root / "a.txt").exists()


@pytest.mark.parametrize("payload", [[], {"rule": "invalid"}, {"rule": []},
    {"excluded_extensions": ".exe"}, {"excluded_extensions": [1]},
    {"excluded_extensions": ["../txt"]}, {"excluded_extensions": [""]}, {"unknown": True}])
def test_settings_reject_invalid_input_without_changing_saved_settings(tmp_path, payload):
    with create_app(data_directory=tmp_path / "data").test_client() as client:
        before = client.get("/api/settings").get_json()
        assert client.post("/api/settings", json=payload).status_code == 400
        assert client.get("/api/settings").get_json() == before


def test_api_missing_history_invalid_options_and_internal_folder(tmp_path):
    data = tmp_path / "data"
    with create_app(data_directory=data).test_client() as client:
        assert client.get("/api/history").get_json() == {"history": []}
        assert client.get("/api/history/missing/undo-preview").status_code == 404
        assert client.post("/api/history/missing/undo", json={"confirmed": True}).status_code == 404
        for payload in ([1], {"folder": None}, {"folder": str(tmp_path), "rule": "bad"},
                        {"folder": str(data)}):
            assert client.post("/api/preview", json=payload).status_code == 400


def test_journal_failure_prevents_moves_and_allows_retry(tmp_path):
    root = tmp_path / "files"
    make_files(root, "a.txt")
    storage = LocalState(tmp_path / "data")
    jobs = JobManager(storage)
    preview = PreviewStore().create(str(root))
    with patch.object(storage, "save_run", side_effect=sqlite3.OperationalError("disk full")):
        with pytest.raises(sqlite3.OperationalError):
            jobs.start(preview)
    assert (root / "a.txt").is_file()
    job = jobs.start(preview)
    deadline = time.monotonic() + 5
    while job.status in ("queued", "running"):
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert job.result.success_count == 1


def test_busy_jobs_and_only_latest_undo(tmp_path):
    root = tmp_path / "files"
    make_files(root, "a.txt")
    jobs = JobManager(LocalState(tmp_path / "data"))
    preview = PreviewStore().create(str(root))
    jobs._operation_lock.acquire()
    try:
        with pytest.raises(ValueError):
            jobs.start(preview)
        with pytest.raises(ValueError):
            jobs.undo("anything")
    finally:
        jobs._operation_lock.release()
    with create_app(job_manager=jobs).test_client() as client:
        first = finish(client, client.post("/api/preview", json={"folder": str(root)}).get_json())
        make_files(root, "b.pdf")
        finish(client, client.post("/api/preview", json={"folder": str(root)}).get_json())
        assert client.post(f"/api/history/{first['job_id']}/undo", json={"confirmed": True}).status_code == 409


def test_permission_failure_is_friendly_and_other_files_continue(tmp_path):
    make_files(tmp_path, "a.txt", "b.pdf")
    plan = create_organization_plan(tmp_path)
    from organizer import move_without_overwrite

    def move(source, destination):
        if source.name == "a.txt":
            raise PermissionError("[WinError 5] sensitive internals")
        move_without_overwrite(source, destination)

    with patch("organizer.move_without_overwrite", side_effect=move):
        result = execute_organization_plan(plan)
    assert (result.success_count, result.failure_count) == (1, 1)
    assert "WinError" not in result.failed_files[0].message
    assert "権限" in result.failed_files[0].message


def test_cli_service_records_history_and_supports_web_undo(tmp_path):
    root, data = tmp_path / "files", tmp_path / "data"
    make_files(root, "cli.txt")
    result = organize_with_history(root, state=LocalState(data))
    assert (result.success_count, result.failure_count) == (1, 0)
    with create_app(data_directory=data).test_client() as client:
        run = client.get("/api/history").get_json()["history"][0]
        response = client.post(f"/api/history/{run['run_id']}/undo", json={"confirmed": True})
        assert response.status_code == 200
        assert response.get_json()["success_count"] == 1
        assert (root / "cli.txt").read_text() == "contents:cli.txt"


def test_storage_api_errors_do_not_expose_technical_details(tmp_path):
    state = LocalState(tmp_path / "data")
    with create_app(job_manager=JobManager(state)).test_client() as client:
        with patch.object(state, "history", side_effect=sqlite3.DatabaseError("private details")):
            response = client.get("/api/history")
            assert response.status_code == 503
            assert "private details" not in response.get_data(as_text=True)
        with patch.object(state, "save_settings", side_effect=PermissionError("private details")):
            response = client.post("/api/settings", json={"rule": "type"})
            assert response.status_code == 503
            assert "private details" not in response.get_data(as_text=True)


def test_failed_post_move_journal_keeps_recoverable_intent(tmp_path):
    root, data = tmp_path / "files", tmp_path / "data"
    make_files(root, "a.txt", "b.pdf")
    state = LocalState(data)
    real_save = state.save_run
    calls = 0

    def failing_save(run):
        nonlocal calls
        calls += 1
        if calls >= 3:
            raise sqlite3.OperationalError("disk full")
        real_save(run)

    manager = JobManager(state)
    with patch.object(state, "save_run", side_effect=failing_save):
        job = manager.start(PreviewStore().create(str(root)))
        assert job.finished.wait(5)
    assert job.status == "failed"
    stored = state.get_run(job.job_id)
    assert len(stored["moves"]) == 1
    assert stored["moves"][0]["status"] == "pending"
    result = JobManager(LocalState(data)).undo(job.job_id)
    assert (result["success_count"], result["failure_count"]) == (1, 0)
    assert (root / "a.txt").read_text() == "contents:a.txt"
    assert (root / "b.pdf").read_text() == "contents:b.pdf"
