from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
datas, binaries, hiddenimports = collect_all('webview')
datas += [(str(root / 'templates'), 'templates'), (str(root / 'static'), 'static')]
icon = root / 'icons' / 'app.ico'
if icon.is_file():
    datas += [(str(icon), 'icons')]
a = Analysis([str(root / 'desktop_app.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'gi'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='File Organizer',
          console=False, debug=False, upx=False,
          icon=str(icon) if icon.is_file() else None)
coll = COLLECT(exe, a.binaries, a.datas, name='File Organizer', upx=False)
