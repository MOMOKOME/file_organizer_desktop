"""Keep test history separate from the user's application history."""

import pytest

import local_state


@pytest.fixture(autouse=True)
def isolated_default_state(tmp_path, monkeypatch):
    monkeypatch.setattr(local_state, "DEFAULT_DATA_DIRECTORY", tmp_path / "app-state")
