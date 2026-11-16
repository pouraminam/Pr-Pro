@echo off
REM Premiere AI Editor Local Engine Launcher for Windows
setlocal enabledelayedexpansion

set ENGINE_DIR=%~dp0..\..\engine
set PYTHON_CMD=python

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%~dp0..\runtime\python.exe" (
        set PYTHON_CMD=%~dp0..\runtime\python.exe
    ) else (
        echo [ERROR] Python not found. Please run install.ps1 first.
        pause
        exit /b 1
    )
)

echo Starting Premiere AI Editor Local Engine on 127.0.0.1:8990...
"%PYTHON_CMD%" -m engine.main --port 8990
