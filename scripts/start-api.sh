#!/usr/bin/env bash
# Always use the project venv (avoids Anaconda uvicorn missing python-multipart)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Create venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

export PYTHONPATH="$ROOT"
exec .venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
