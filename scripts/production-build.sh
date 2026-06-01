#!/usr/bin/env bash
# Build frontend for production (run on server or CI after git pull)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
npm ci
npm run build
echo "Built: $ROOT/frontend/dist"
