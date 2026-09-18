@echo off
echo ============================================
echo  CRM Support Ticket AI System
echo ============================================
echo.

REM Warn if .env is missing but still continue
if not exist ".env" (
    echo [WARNING] .env file not found - NL Query and Anomaly Summary will not work.
    echo To enable AI features: copy .env.example .env and add your GROQ_API_KEY
    echo Get your free key at: https://console.groq.com
    echo.
    echo Starting anyway with data-only mode...
    echo.
)

echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "FastAPI Backend" cmd /k "cd /d %~dp0 && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak > nul

echo [2/2] Starting Streamlit UI on http://localhost:8501 ...
start "Streamlit UI" cmd /k "cd /d %~dp0 && streamlit run ui/streamlit_app.py --server.port 8501"

echo.
echo ============================================
echo  Both services are starting!
echo  API:      http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo  UI:       http://localhost:8501
echo ============================================
echo.
echo Wait ~5 seconds then open http://localhost:8501 in your browser.
pause
