@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_installer.ps1" %*
if errorlevel 1 (
    echo.
    echo IPHunter installer build failed.
    exit /b 1
)
echo.
echo IPHunter installer build completed.
endlocal
