#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
source ~/venv/bin/activate

mkdir -p logs

python -m uvicorn api:app --host 0.0.0.0 --port 8060 > logs/api.log 2>&1 &
API_PID=$!

python monitor.py --interval 30 > logs/monitor.log 2>&1 &
MONITOR_PID=$!

python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!

cleanup() {
    kill "$API_PID" "$MONITOR_PID" "$DASHBOARD_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "RunbookMemory AI started"
echo "Dashboard: http://localhost:8501"
echo "API:       http://localhost:8060/docs"
echo "Logs:      $(pwd)/logs"
echo "Press Ctrl+C to stop all services"

wait
