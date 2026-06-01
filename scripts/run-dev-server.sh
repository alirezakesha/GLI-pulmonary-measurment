#!/usr/bin/env bash
# Run API in development mode on the server (no systemd).
# Usage (on EC2):
#   cd /opt/gli-pft/GLI-pulmonary-measurment
#   chmod +x scripts/run-dev-server.sh
#   ./scripts/run-dev-server.sh
#
# Then either:
#   - Open EC2:8000/docs if security group allows port 8000
#   - Or SSH tunnel from laptop:  ssh -L 8000:127.0.0.1:8000 user@EC2
#     and open http://127.0.0.1:8000/docs

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-*}"

VENV_UVICORN="$ROOT/.venv/bin/uvicorn"
if [[ ! -x "$VENV_UVICORN" ]]; then
  echo "ERROR: $VENV_UVICORN not found."
  echo "  cd $ROOT && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Project root: $ROOT"
echo "PYTHONPATH:   $PYTHONPATH"
echo "API:          http://127.0.0.1:8000  (docs: /docs)"
echo "Health:       http://127.0.0.1:8000/api/health"
echo ""
echo "Press Ctrl+C to stop."
echo ""

exec "$VENV_UVICORN" backend.app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
