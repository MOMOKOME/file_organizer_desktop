"""Application identity and paths shared by development and frozen builds."""
import os
import sys
from pathlib import Path

APP_NAME = "File Organizer"
BRAND = "MOMONGA Lab"
VERSION = "3.2.0"


def resource_path(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def user_data_directory():
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "MOMONGA_Lab" / "FileOrganizer"


# GUI editions differ only in the screen; engine, API, data folder and lock are shared.
EDITIONS = {"simple": "File Organizer", "classic": "File Organizer Classic"}
EDITION_ENV = "FILE_ORGANIZER_EDITION"
EDITION_MARKER = "edition.txt"


def detect_edition():
    """Frozen builds trust only the bundled marker; development reads the env var."""
    if getattr(sys, "frozen", False):
        try:
            value = resource_path(EDITION_MARKER).read_text(encoding="utf-8")
        except OSError:
            value = "simple"
    else:
        value = os.environ.get(EDITION_ENV, "simple")
    value = value.strip().lower()
    return value if value in EDITIONS else "simple"


EDITION = detect_edition()
DISPLAY_NAME = EDITIONS[EDITION]
