#!/usr/bin/env bash
# Build frontend for production (run on server or on your laptop)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not installed or not in PATH." >&2
  echo "" >&2
  echo "On Ubuntu EC2, install Node.js 20 LTS:" >&2
  echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -" >&2
  echo "  sudo apt install -y nodejs" >&2
  echo "  node -v && npm -v" >&2
  echo "" >&2
  echo "Or build on your Mac and copy dist/ to the server (no Node on server):" >&2
  echo "  cd frontend && npm ci && npm run build" >&2
  echo "  rsync -avz frontend/dist/ ubuntu@YOUR_SERVER:/opt/gli-pft/GLI-pulmonary-measurment/frontend/dist/" >&2
  exit 1
fi

if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

# Optional: serve under a subpath (e.g. www.example.com/gli/)
# Usage: VITE_BASE_PATH=/gli/ ./scripts/production-build.sh
export VITE_BASE_PATH="${VITE_BASE_PATH:-/}"
echo "Building with VITE_BASE_PATH=${VITE_BASE_PATH}"
npm run build
echo "Built: $ROOT/frontend/dist"
