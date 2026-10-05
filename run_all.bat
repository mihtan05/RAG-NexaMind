@echo off
title NexaMind AI - Fullstack Launcher
cd /d "%~dp0"

echo ========================================================
echo   NexaMind AI - He thong RAG Hoi dap Doanh nghiep
echo ========================================================
echo.

:: 1. Tu dong khoi tao file .env neu chua ton tai
if not exist ".env" (
    echo [*] Phat hien chua co .env - Dang tao tu .env.example...
    copy .env.example .env >nul
    echo [!] Chu y: Vui long dien GEMINI_API_KEY vao file .env de su dung AI!
    echo.
)

:: 2. Tu dong khoi tao Virtual Environment va cai thu vien Python neu chua co
if not exist ".venv\Scripts\python.exe" (
    echo [*] Phat hien chay lan dau - Dang khoi tao Python .venv...
    python -m venv .venv
    echo [*] Dang tu dong cai dat thu vien Python (requirements.txt)...
    call .venv\Scripts\pip install -r requirements.txt
    echo.
)

:: 3. Tu dong cai dat thu vien Frontend neu chua co node_modules
if not exist "frontend\node_modules" (
    echo [*] Phat hien chua cai thu vien Frontend - Dang chay npm install...
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
    echo.
)

:: 4. Kiem tra va khoi dong PostgreSQL container neu Docker dang chay
docker info >nul 2>&1
if not errorlevel 1 (
    echo [*] Docker dang hoat dong - Khoi dong PostgreSQL container...
    docker compose up -d postgres >nul 2>&1
    echo [*] PostgreSQL da san sang tren localhost:5432!
) else (
    echo [i] Docker khong bat - He thong se dung SQLite du phong (data/nexamind.db).
)
echo.

:: 5. Khoi dong Backend FastAPI (Port 8000)
echo [*] Dang khoi dong FastAPI Backend tren http://127.0.0.1:8000 ...
start "NexaMind Backend (Port 8000)" cmd /k "cd /d "%~dp0" && call .venv\Scripts\activate.bat && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

:: 6. Khoi dong React Frontend (Port 5173)
echo [*] Dang khoi dong React Frontend tren http://127.0.0.1:5173 ...
start "NexaMind Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================================
echo   He thong da duoc khoi dong:
echo   - Web App UI:   http://127.0.0.1:5173
echo   - API Swagger:  http://127.0.0.1:8000/docs
echo ========================================================
echo.

:: 7. Tu dong mo trinh duyet sau 3 giay
timeout /t 3 >nul
start http://127.0.0.1:5173
