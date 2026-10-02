#!/usr/bin/env bash
# Njangi Tracker - FRONTEND update script.
#
# Pulls the latest code from Git, sanity-checks the pages and scripts, and
# (optionally) publishes the files to your web server folder.
#
# Usage:   ./update.sh
#          DEPLOY_DIR=/var/www/njangi ./update.sh
#
# Optional settings (environment variables):
#   BRANCH       Git branch to pull           (default: current branch)
#   DEPLOY_DIR   Web-root folder to publish to (e.g. /var/www/njangi). If unset,
#                the files are served from this folder and nothing is copied.
#   SERVICE      systemd service that runs serve.py, restarted if it exists
#                (default: njangi-frontend)
set -euo pipefail

cd "$(dirname "$0")"
FRONTEND_DIR="$(pwd)"
SERVICE="${SERVICE:-njangi-frontend}"
DEPLOY_DIR="${DEPLOY_DIR:-}"

say()  { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mxx %s\033[0m\n' "$*" >&2; exit 1; }

[ -f index.html ] && [ -f js/config.js ] || die "This does not look like the Frontend folder (index.html / js/config.js missing)."

# ---- 1. Pull the latest code ----------------------------------------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "Pulling latest code"
  BEFORE="$(git rev-parse --short HEAD)"
  BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  git fetch -q --prune origin
  if ! git diff --quiet || ! git diff --cached --quiet; then
    die "You have uncommitted changes. Commit or stash them, then run update.sh again."
  fi
  git pull -q --ff-only origin "$BRANCH"
  AFTER="$(git rev-parse --short HEAD)"
  if [ "$BEFORE" = "$AFTER" ]; then echo "Already up to date ($AFTER)."; else echo "Updated $BEFORE -> $AFTER"; git --no-pager log --oneline "$BEFORE..$AFTER" | head -20; fi
else
  warn "Not a git repository - skipping pull (copy the new files in manually, then re-run)."
fi

# ---- 2. Sanity checks ------------------------------------------------------
say "Checking the frontend"
PROBLEMS=0

# every <script src>, stylesheet and page link must exist
while IFS= read -r ref; do
  [ -e "$ref" ] || { warn "Missing file referenced by an HTML page: $ref"; PROBLEMS=$((PROBLEMS + 1)); }
done < <(grep -hoE '(src|href)="(js|css)/[^"?#]+' ./*.html | sed -E 's/^(src|href)="//' | sort -u)

# JavaScript syntax (needs Node; skipped if not installed)
if command -v node >/dev/null 2>&1; then
  for f in js/*.js; do
    node --check "$f" 2>/dev/null || { warn "JavaScript syntax error in $f"; PROBLEMS=$((PROBLEMS + 1)); }
  done
else
  warn "Node.js not installed - skipping JavaScript syntax check."
fi

# Production reminder: the API address must be set when not running locally
if [ -n "$DEPLOY_DIR" ] && grep -qE "PRODUCTION_API = ''" js/config.js; then
  warn "js/config.js: PRODUCTION_API is empty, so the site will look for the API on port 8000 of the same host."
  warn "Set PRODUCTION_API to your backend URL (ending in /api) if the backend is elsewhere."
fi

[ "$PROBLEMS" -eq 0 ] || die "$PROBLEMS problem(s) found - not publishing."
echo "All checks passed."

# ---- 3. Publish ------------------------------------------------------------
if [ -n "$DEPLOY_DIR" ]; then
  say "Publishing to $DEPLOY_DIR"
  SUDO=""; [ ! -w "$DEPLOY_DIR" ] 2>/dev/null && [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
  $SUDO mkdir -p "$DEPLOY_DIR"
  EXCLUDES=(--exclude '.git' --exclude '.gitignore' --exclude 'README.md' --exclude 'update.sh' --exclude 'start.sh' --exclude 'start.bat' --exclude 'serve.py' --exclude '.env')
  if command -v rsync >/dev/null 2>&1; then
    $SUDO rsync -a --delete "${EXCLUDES[@]}" ./ "$DEPLOY_DIR"/
  else
    warn "rsync not found - using cp (deleted files will not be removed)."
    $SUDO cp -r ./*.html ./css ./js ./favicon.svg "$DEPLOY_DIR"/
  fi
  echo "Published."
else
  # Served straight from this folder: restart serve.py if it runs as a service.
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE}\.service"; then
    say "Restarting $SERVICE"
    SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
    $SUDO systemctl restart "$SERVICE"
  else
    echo "Static files are served directly from this folder - no restart needed."
  fi
fi

say "Frontend is up to date."
