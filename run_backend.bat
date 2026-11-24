@echo off
setlocal
cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo [Setup] Creating Python virtual environment...
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -m venv venv
    ) else (
        python -m venv venv
    )
    if errorlevel 1 (
        echo [Error] Failed to create venv. Please install Python 3.
        pause
        exit /b 1
    )
    echo [Setup] Installing backend dependencies...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Error] Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

echo [Backend] Starting FastAPI at http://127.0.0.1:8000 (Swagger: /docs, 1 worker)...
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000 --workers 1
if errorlevel 1 pause
