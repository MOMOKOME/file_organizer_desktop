@echo off
setlocal EnableExtensions
title File Organizer Web
chcp 65001 >nul

pushd "%~dp0"
if errorlevel 1 goto path_error

set "APP_PORT=5000"
set "PYTHON_CMD="

echo ================================================
echo File Organizer Web - Startup
echo ================================================
echo [1/3] Checking Python...

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_found
)

goto python_missing

:python_found
%PYTHON_CMD% --version
if errorlevel 1 goto python_missing

echo [2/3] Checking required packages...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip was not found. Restoring pip...
    %PYTHON_CMD% -m ensurepip --upgrade
    if errorlevel 1 goto dependency_error
)

%PYTHON_CMD% -m pip show Flask >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    %PYTHON_CMD% -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto dependency_error
)

echo [3/3] Starting the web app...
echo URL: http://127.0.0.1:%APP_PORT%
echo Keep this window open while using the app.
echo Press Ctrl+C to stop the app.
echo ================================================

if /i "%FILE_ORGANIZER_NO_BROWSER%"=="1" goto run_without_browser
%PYTHON_CMD% web_app.py --port %APP_PORT%
goto app_stopped

:run_without_browser
%PYTHON_CMD% web_app.py --no-browser --port %APP_PORT%

:app_stopped
set "APP_EXIT=%ERRORLEVEL%"
if "%APP_EXIT%"=="0" goto normal_exit
echo.
echo ERROR: The web app stopped with exit code %APP_EXIT%.
echo Check whether port %APP_PORT% is already in use and review the error above.
pause
popd
exit /b %APP_EXIT%

:path_error
echo ERROR: Could not open the application folder.
pause
exit /b 1

:python_missing
echo.
echo ERROR: Python 3 was not found.
echo Install Python 3 and enable the Python Launcher or add Python to PATH.
pause
popd
exit /b 1

:dependency_error
echo.
echo ERROR: Required Python packages could not be installed.
echo Check the internet connection and the messages above.
pause
popd
exit /b 1

:normal_exit
popd
endlocal
