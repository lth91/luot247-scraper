#!/bin/bash
# Entrypoint chạy bởi LaunchAgent mỗi giờ.
# 1. cd vào repo, pull code mới
# 2. activate venv
# 3. chạy scraper, log ra ~/.openclaw/logs/luot247-scraper.log

set -euo pipefail

REPO_DIR="${LUOT247_REPO_DIR:-$HOME/.openclaw/skills/luot247-scraper}"
VENV="${LUOT247_VENV:-$HOME/.openclaw/venv-luot247}"
ENV_FILE="${LUOT247_ENV:-$HOME/.openclaw/luot247-scraper.env}"
LOG_DIR="$HOME/.openclaw/logs"
LOG_FILE="$LOG_DIR/luot247-scraper.log"

mkdir -p "$LOG_DIR"

{
  echo "===== $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
  cd "$REPO_DIR"

  # Pull code mới (skip nếu offline)
  git pull --ff-only --quiet || echo "[warn] git pull failed (offline?), continuing with current code"

  # Activate venv + run
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"

  # Truyền env qua biến — script tự load .env
  export LUOT247_ENV="$ENV_FILE"

  python "$REPO_DIR/scraper.py"
} >> "$LOG_FILE" 2>&1
