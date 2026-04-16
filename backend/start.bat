@echo off
echo Starting FinTrack Pro...

cd C:\Users\Lenovo\Downloads\CFA\finance_app\backend

REM Terminal 1: API Server
start "FinTrack API" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

REM Wait 3 seconds for API to start
timeout /t 3 /nobreak

REM Terminal 2: Data Scheduler
start "FinTrack Scheduler" cmd /k "python scheduler.py"

REM Wait 2 more seconds then open browser
timeout /t 2 /nobreak
start "" "http://localhost:8000/index.html"

echo Done! Both windows opened.