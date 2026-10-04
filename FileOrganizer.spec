from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
datas, binaries, hiddenimports = collect_all('webview')
# webview.__pyinstaller is pywebview's build-time hook. It imports PyInstaller, whose
# build modules are GPL and must not be shipped; the app never uses it at runtime.
hiddenimports = [m for m in hiddenimports if not m.startswith('webview.__pyinstaller')]
datas = [(src, dest) for src, dest in datas if '__pyinstaller' not in Path(dest).parts]
datas += [(str(root / 'templates'), 'templates'), (str(root / 'static'), 'static')]
icon = root / 'icons' / 'app.ico'
if icon.is_file():
    datas += [(str(icon), 'icons')]
a = Analysis([str(root / 'desktop_app.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             # Build tools are not runtime dependencies (setuptools is only reached via
             # cffi's compile helpers, which ABI-mode clr_loader does not use).
             excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'gi',
                       'PyInstaller', 'setuptools', '_distutils_hack', 'pkg_resources'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='File Organizer',
          console=False, debug=False, upx=False,
          icon=str(icon) if icon.is_file() else None)
coll = COLLECT(exe, a.binaries, a.datas, name='File Organizer', upx=False)
