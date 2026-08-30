#!/usr/bin/env bash
#
# dev-fpl.sh — run the FPL backend (this repo) and the frontend together for local dev.
#   Backend : FastAPI  → http://127.0.0.1:8000  (docs at /docs)
#   Frontend: Vite/npm → http://localhost:8080
# Stop both with Ctrl+C.
#
set -euo pipefail

BE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FE_DIR="$BE_DIR/../fpl-season-review"

trap 'echo; echo "Shutting down..."; kill 0' EXIT INT TERM

# --- Backend ---
cd "$BE_DIR"
if [ -d venv ]; then
  source venv/bin/activate
elif [ -d fpl-env ]; then
  source fpl-env/bin/activate
else
  echo "No venv found in $BE_DIR (expected venv/ or fpl-env/)." >&2
  exit 1
fi
# Free port 8000 if a previous run left an orphaned uvicorn behind.
# `--reload` spawns a reloader parent + worker child; a plain SIGTERM to one of
# them is often ignored, so kill EVERY pid on the port and escalate to -9.
STALE_PIDS="$(lsof -nP -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$STALE_PIDS" ]; then
  echo "[backend]  port 8000 busy (pids: $STALE_PIDS) — killing"
  kill $STALE_PIDS 2>/dev/null || true
  sleep 1
  # Anything still holding the port gets SIGKILL.
  STILL="$(lsof -nP -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$STILL" ]; then
    echo "[backend]  still busy (pids: $STILL) — SIGKILL"
    kill -9 $STILL 2>/dev/null || true
    sleep 1
  fi
fi

echo "[backend]  starting uvicorn on :8000"
# use `python -m` so we always run THIS venv's uvicorn, not a global pipx one
python -m uvicorn app.main:app --reload --port 8000 &

# --- Frontend ---
if [ ! -d "$FE_DIR" ]; then
  echo "Frontend not found at $FE_DIR" >&2
  exit 1
fi
cd "$FE_DIR"
echo "[frontend] starting vite on :8080"
npm run dev &

wait
