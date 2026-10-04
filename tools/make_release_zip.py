"""Package the PyInstaller output into the Windows distribution ZIP.

Run after `python -m PyInstaller --noconfirm --clean FileOrganizer.spec`:

    python tools/make_release_zip.py

1. Copies the user-facing documents next to `File Organizer.exe`
   (TERMS_OF_USE.txt, PRIVACY.txt, THIRD_PARTY_NOTICES.txt, THIRD_PARTY_LICENSES/).
2. Zips the whole `dist/File Organizer` folder (onedir layout preserved) into
   `dist/release-<version>/FileOrganizer-<version>-win-x64.zip`.
3. Writes `SHA256SUMS.txt` next to the ZIP.
"""
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_config import APP_NAME, VERSION  # noqa: E402

APP_DIR = ROOT / "dist" / APP_NAME
RELEASE_DIR = ROOT / "dist" / f"release-{VERSION}"
ZIP_NAME = f"FileOrganizer-{VERSION}-win-x64.zip"
DOCUMENTS = ["TERMS_OF_USE.md", "PRIVACY.md", "THIRD_PARTY_NOTICES.md"]


def copy_documents():
    for name in DOCUMENTS:
        text = (ROOT / name).read_text(encoding="utf-8")
        # .txt with a UTF-8 BOM so Windows Notepad always shows the Japanese text correctly.
        (APP_DIR / name.replace(".md", ".txt")).write_text(text, encoding="utf-8-sig")
    licenses = APP_DIR / "THIRD_PARTY_LICENSES"
    if licenses.exists():
        shutil.rmtree(licenses)
    shutil.copytree(ROOT / "THIRD_PARTY_LICENSES", licenses)  # copied byte-for-byte


def make_zip():
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    target = RELEASE_DIR / ZIP_NAME
    files = sorted(path for path in APP_DIR.rglob("*") if path.is_file())
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(APP_DIR.parent).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity check failed")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (RELEASE_DIR / "SHA256SUMS.txt").write_text(f"{digest} *{ZIP_NAME}\n", encoding="ascii")
    return target, digest, len(files)


def main():
    if not (APP_DIR / f"{APP_NAME}.exe").is_file():
        raise SystemExit(f"Build first: {APP_DIR / (APP_NAME + '.exe')} not found")
    copy_documents()
    target, digest, count = make_zip()
    print(f"{target.relative_to(ROOT)}: {count} files, {target.stat().st_size} bytes")
    print(f"SHA256: {digest}")


if __name__ == "__main__":
    main()
