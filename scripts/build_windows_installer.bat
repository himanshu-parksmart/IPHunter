@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_installer.ps1" %*
set "BUILD_EXIT_CODE=%ERRORLEVEL%"
if not "%BUILD_EXIT_CODE%"=="0" (
    echo.
    echo IPHunter installer build failed.
    exit /b %BUILD_EXIT_CODE%
)
echo.
echo IPHunter installer build completed.
endlocal
