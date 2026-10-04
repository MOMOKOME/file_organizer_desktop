@echo off
setlocal
cd /d "%~dp0"
if not defined FILE_ORGANIZER_BUILD_PYTHON set "FILE_ORGANIZER_BUILD_PYTHON=python"
"%FILE_ORGANIZER_BUILD_PYTHON%" --version
if errorlevel 1 goto fail
if not exist .venv-build\Scripts\python.exe (
  "%FILE_ORGANIZER_BUILD_PYTHON%" -m venv .venv-build
  if errorlevel 1 goto fail
)
.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto fail
.venv-build\Scripts\python.exe -m pytest tests -q -o pythonpath=.
if errorlevel 1 goto fail
.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean FileOrganizer.spec
if errorlevel 1 goto fail
echo SUCCESS: dist\File Organizer\File Organizer.exe
echo Distribute the entire File Organizer directory.
if not "%~1"=="--no-pause" pause
exit /b 0
:fail
echo BUILD FAILED. See the error above.
if not "%~1"=="--no-pause" pause
exit /b 1
