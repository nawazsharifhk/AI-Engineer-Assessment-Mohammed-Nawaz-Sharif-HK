#!/bin/bash
set -e

echo "============================================"
echo " CRM Support Ticket AI System"
echo "============================================"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[ERROR] .env file not found!"
    echo "Please copy .env.example to .env and add your GROQ_API_KEY"
    echo "Get your free key at: https://console.groq.com"
    exit 1
fi

echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 4

echo "[2/2] Starting Streamlit UI on http://localhost:8501 ..."
streamlit run ui/streamlit_app.py --server.port 8501 &
UI_PID=$!

echo ""
echo "============================================"
echo " Both services started!"
echo " API:      http://localhost:8000"
echo " API Docs: http://localhost:8000/docs"
echo " UI:       http://localhost:8501"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services."

wait $BACKEND_PID $UI_PID
