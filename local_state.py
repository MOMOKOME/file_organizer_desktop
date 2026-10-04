"""Local SQLite metadata only: settings, execution journal and Undo results."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from organization_rules import normalize_options
from app_config import user_data_directory

DEFAULT_DATA_DIRECTORY = user_data_directory()


def now():
    return datetime.now(timezone.utc).isoformat()


def file_identity(path):
    stat = path.stat(follow_symlinks=False)
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]


class LocalState:
    def __init__(self, directory=None):
        self.directory = Path(directory or DEFAULT_DATA_DIRECTORY).resolve()
        self._lock = RLock()

    @contextmanager
    def _connect(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.directory / "state.sqlite3", timeout=10)
        try:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
                yield connection
        finally:
            connection.close()

    def settings(self):
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT data FROM settings WHERE id=1").fetchone()
            return normalize_options(**json.loads(row[0])) if row else normalize_options()

    def save_settings(self, rule="extension", excluded_extensions=None):
        settings = normalize_options(rule, excluded_extensions)
        with self._lock, self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO settings VALUES (1, ?)",
                               (json.dumps(settings),))
        return settings

    def save_run(self, run):
        with self._lock, self._connect() as connection:
            connection.execute("INSERT INTO runs VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                               (run["run_id"], json.dumps(run, ensure_ascii=False)))

    def history(self):
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT data FROM runs ORDER BY rowid DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_run(self, run_id):
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
