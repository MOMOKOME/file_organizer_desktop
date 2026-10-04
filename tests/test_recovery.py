"""Saved CLI options and interrupted execution recovery."""
from unittest.mock import patch

from local_state import LocalState
from organizer import execute_organization_plan
from organizer_service import JobManager, PreviewStore, organize_with_history


def test_cli_restores_settings_and_explicit_overrides(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "photo.JPG").write_text("photo")
    (root / "keep.TMP").write_text("keep")
    state = LocalState(tmp_path / "state")
    state.save_settings("type", [".tmp"])
    result = organize_with_history(root, state=state)
    assert (result.success_count, result.failure_count) == (1, 0)
    assert (root / "画像" / "photo.JPG").read_text() == "photo"
    assert (root / "keep.TMP").read_text() == "keep"
    assert state.history()[0]["rule"] == "type"
    result = organize_with_history(root, rule="extension", excluded_extensions=[], state=state)
    assert result.success_count == 1
    assert (root / "tmp" / "keep.TMP").read_text() == "keep"
    assert state.settings() == {"rule": "extension", "excluded_extensions": []}


def test_worker_failure_records_interruption_and_recovers(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("original")
    state = LocalState(tmp_path / "state")
    manager = JobManager(state)

    def interrupted_move(plan):
        execute_organization_plan(plan)
        raise RuntimeError("interruption after move")

    with patch("organizer_service.execute_organization_plan", side_effect=interrupted_move):
        job = manager.start(PreviewStore().create(str(root)))
        assert job.finished.wait(5)
    assert job.status == "failed"
    run = state.get_run(job.job_id)
    assert run["status"] == "interrupted"
    assert run["moves"][0]["status"] == "pending"
    result = JobManager(LocalState(state.directory)).undo(job.job_id)
    assert (result["success_count"], result["failure_count"]) == (1, 0)
    assert (root / "a.txt").read_text() == "original"


def test_undo_rechecks_identity_at_execution_and_continues(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a.txt").write_text("original")
    (root / "b.pdf").write_text("safe")
    state = LocalState(tmp_path / "state")
    organize_with_history(root, state=state)
    run = state.history()[0]

    def changed_after_check(plan):
        if plan.plans[0].source.name == "a.txt":
            plan.plans[0].source.write_text("new user contents")
        return execute_organization_plan(plan)

    with patch("organizer_service.execute_organization_plan", side_effect=changed_after_check):
        result = JobManager(state).undo(run["run_id"])
    assert (result["success_count"], result["failure_count"]) == (1, 1)
    assert not (root / "a.txt").exists()
    assert (root / "txt" / "a.txt").read_text() == "new user contents"
    assert (root / "b.pdf").read_text() == "safe"
