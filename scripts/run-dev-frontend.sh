#!/usr/bin/env bash
# Run Vite dev server (needs npm). Proxies /api to localhost:8000.
# Start scripts/run-dev-server.sh in another terminal first.
#
# Usage:
#   cd /opt/gli-pft/GLI-pulmonary-measurment
#   ./scripts/run-dev-frontend.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not installed. Install Node 20 or build locally and use production nginx later."
  exit 1
fi

echo "UI dev server: http://127.0.0.1:5173  (proxies /api → :8000)"
echo "Ensure API is running: ./scripts/run-dev-server.sh"
echo ""

npm run dev -- --host 127.0.0.1 --port 5173
