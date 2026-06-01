#!/usr/bin/env bash
# Start API + frontend (run from project root)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Create venv first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

export PYTHONPATH="$ROOT"

.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!

cd frontend
npm run dev &
WEB_PID=$!

trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
echo "API:  http://127.0.0.1:8000/docs"
echo "App:  http://127.0.0.1:5173"
wait
