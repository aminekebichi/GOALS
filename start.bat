@echo off
setlocal

echo.
echo  ==========================================
echo   GOALS -- Game Outcome Analytics System
echo  ==========================================
echo.

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [1/4] Virtual environment activated.
) else (
    echo [WARN] No .venv found. Using system Python.
)

:: Build frontend
echo [2/4] Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed. Run: cd frontend ^&^& npm install
    exit /b 1
)
cd ..
echo [2/4] Frontend built.

:: Open browser after a short delay (background)
echo [3/4] Opening browser...
start /min "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"

:: Start FastAPI
echo [4/4] Starting server at http://localhost:8000
echo        Press Ctrl+C to stop.
echo.
uvicorn goals_app.main:app --host 127.0.0.1 --port 8000

endlocal
