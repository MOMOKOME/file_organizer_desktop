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
