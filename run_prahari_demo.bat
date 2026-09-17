@echo off
cd /d "%~dp0"
echo Launching prahari demo...
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\demo_windows.ps1"
echo.
echo Script finished with exit code %errorlevel%.
pause
