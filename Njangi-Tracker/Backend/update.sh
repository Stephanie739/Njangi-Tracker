#!/usr/bin/env bash
# Njangi Tracker - BACKEND update script.
#
# Pulls the latest code from Git, backs up the database, checks the code
# compiles, restarts the API and verifies /api/health.
#
# Usage:   ./update.sh            (run from anywhere)
#          BRANCH=main ./update.sh
#
# Optional settings (environment variables):
#   BRANCH        Git branch to pull          (default: current branch)
#   SERVICE       systemd service name        (default: njangi-backend)
#   PM2_NAME      pm2 process name            (default: njangi-backend)
#   PORT          API port for health check   (default: 8000)
#   KEEP_BACKUPS  number of DB backups to keep (default: 10)
#
# Your .env and njangi_app.db are never touched by git (they are in .gitignore).
set -euo pipefail

cd "$(dirname "$0")"
BACKEND_DIR="$(pwd)"
SERVICE="${SERVICE:-njangi-backend}"
PM2_NAME="${PM2_NAME:-njangi-backend}"
PORT="${PORT:-8000}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"
PY="$(command -v python3 || command -v python || true)"

say()  { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mxx %s\033[0m\n' "$*" >&2; exit 1; }

[ -n "$PY" ] || die "Python 3 is not installed."
[ -f server.py ] || die "server.py not found in $BACKEND_DIR"

# ---- 1. Back up the database (before anything changes) --------------------
DB_FILE="${NJANGI_DB_PATH:-$BACKEND_DIR/njangi_app.db}"
if [ -f "$DB_FILE" ]; then
  say "Backing up database"
  mkdir -p "$BACKEND_DIR/backups"
  STAMP="$(date +%Y%m%d-%H%M%S)"
  # sqlite3 .backup is safe while the server is running; fall back to python, then cp.
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_FILE" ".backup '$BACKEND_DIR/backups/njangi_app-$STAMP.db'"
  else
    "$PY" - "$DB_FILE" "$BACKEND_DIR/backups/njangi_app-$STAMP.db" <<'PYEOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PYEOF
  fi
  echo "Saved backups/njangi_app-$STAMP.db"
  # keep only the newest N backups
  ls -1t "$BACKEND_DIR"/backups/njangi_app-*.db 2>/dev/null | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm -f
else
  warn "No database at $DB_FILE yet - skipping backup."
fi

# ---- 2. Pull the latest code ----------------------------------------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "Pulling latest code"
  BEFORE="$(git rev-parse --short HEAD)"
  BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  git fetch -q --prune origin
  # Refuse to overwrite local edits to tracked files.
  if ! git diff --quiet || ! git diff --cached --quiet; then
    die "You have uncommitted changes. Commit or stash them, then run update.sh again."
  fi
  git pull -q --ff-only origin "$BRANCH"
  AFTER="$(git rev-parse --short HEAD)"
  if [ "$BEFORE" = "$AFTER" ]; then echo "Already up to date ($AFTER)."; else echo "Updated $BEFORE -> $AFTER"; git --no-pager log --oneline "$BEFORE..$AFTER" | head -20; fi
else
  warn "Not a git repository - skipping pull (copy the new files in manually, then re-run)."
fi

# ---- 3. Check the code before restarting ----------------------------------
say "Checking the code compiles"
"$PY" -m py_compile server.py
find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
[ -f .env ] || warn ".env is missing - copy .env.example to .env and fill in the SMTP settings."

# ---- 4. Restart the API ----------------------------------------------------
say "Restarting the API"
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
RESTARTED=""
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE}\.service"; then
  $SUDO systemctl restart "$SERVICE" && RESTARTED="systemd service '$SERVICE'"
elif command -v pm2 >/dev/null 2>&1 && pm2 describe "$PM2_NAME" >/dev/null 2>&1; then
  pm2 restart "$PM2_NAME" && RESTARTED="pm2 process '$PM2_NAME'"
else
  # No service manager configured: stop ONLY the server.py running from this folder
  # (matched by working directory / full path, so other projects are never touched).
  for pid in $(pgrep -f "server\.py" || true); do
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    if [ "$cwd" = "$BACKEND_DIR" ] || echo "$cmd" | grep -q "$BACKEND_DIR/server.py"; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  sleep 1
  nohup "$PY" "$BACKEND_DIR/server.py" >> "$BACKEND_DIR/server.log" 2>&1 &
  RESTARTED="background process (log: Backend/server.log)"
fi
echo "Restarted: $RESTARTED"

# ---- 5. Health check -------------------------------------------------------
say "Checking /api/health"
if command -v curl >/dev/null 2>&1; then
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS -m 3 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
      echo "API is healthy on port $PORT."; exit 0
    fi
    sleep 1
  done
  die "The API did not answer on port $PORT. Check the logs (journalctl -u $SERVICE, pm2 logs, or Backend/server.log)."
else
  warn "curl not installed - skipping health check."
fi
