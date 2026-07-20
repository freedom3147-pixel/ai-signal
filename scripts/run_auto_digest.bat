@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "LOGDIR=%USERPROFILE%\.ai-signal\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%i"
set "LOG=%LOGDIR%\auto-%STAMP%.log"

echo [%date% %time%] start >> "%LOG%"

REM prepare_digest.py defaults to local blog RSS refresh (generate_feed --blogs-only)
REM so Substack sources blocked on GitHub Actions still enter the digest.
echo [1/3] prepare_digest.py (incl. local blog refresh) >> "%LOG%"
python prepare_digest.py > "%TEMP%\ai_signal_manifest.json" 2>> "%LOG%"
if errorlevel 1 (
    echo FAIL prepare_digest >> "%LOG%"
    exit /b 1
)

echo [2/3] auto_remix.py >> "%LOG%"
python auto_remix.py > "%TEMP%\ai_signal_digest.md" 2>> "%LOG%"
if errorlevel 1 (
    echo FAIL auto_remix >> "%LOG%"
    exit /b 1
)

echo [3/3] deliver.py >> "%LOG%"
python deliver.py --file "%TEMP%\ai_signal_digest.md" --mark-delivered-file "%USERPROFILE%\.ai-signal\payload\delivery-mark.json" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAIL deliver >> "%LOG%"
    exit /b 1
)

echo [%date% %time%] done >> "%LOG%"
endlocal
exit /b 0
