@echo off
setlocal
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo [Setup] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [Error] npm install failed. Please check Node.js installation.
        pause
        exit /b 1
    )
)

echo [Frontend] Starting Vite dev server at http://127.0.0.1:5173 ...
call npm run dev
if errorlevel 1 pause
