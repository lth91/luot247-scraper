#!/bin/bash
# Auto-pull luot247-scraper repo + kickstart scraper khi có commit mới.
# Chạy mỗi 5 min qua LaunchAgent com.luot247.auto-pull.
# Mục tiêu: push code lên GitHub → ≤5 min sau Mac Mini tự apply, zero-touch.
#
# Logic:
#   1. git fetch (silent fail nếu offline)
#   2. Nếu HEAD == origin/main: no-op (không pollute log)
#   3. Nếu có commit mới: pull --ff-only
#      - Skip kickstart nếu scraper đang chạy (tránh interrupt mid-cycle, code
#        mới sẽ tự apply ở cycle kế tiếp tối đa 1h sau)
#      - Còn lại: kickstart com.luot247.scraper ngay

set -uo pipefail

REPO_DIR="${LUOT247_REPO_DIR:-$HOME/.openclaw/skills/luot247-scraper}"
LOG_DIR="$HOME/.openclaw/logs"
LOG_FILE="$LOG_DIR/auto-pull.log"
SCRAPER_LABEL="com.luot247.scraper"

mkdir -p "$LOG_DIR"

cd "$REPO_DIR" || exit 0

if ! git fetch --quiet 2>/dev/null; then
  exit 0
fi

NEW=$(git log HEAD..origin/main --oneline 2>/dev/null)
if [ -z "$NEW" ]; then
  exit 0
fi

{
  echo "===== $(date -u '+%Y-%m-%dT%H:%M:%SZ') ====="
  echo "[auto-pull] new commits:"
  echo "$NEW"

  if ! git pull --ff-only --quiet; then
    echo "[auto-pull] git pull failed (conflict? non-fast-forward?)"
    exit 0
  fi

  if launchctl print "gui/$(id -u)/$SCRAPER_LABEL" 2>/dev/null | grep -q 'state = running'; then
    echo "[auto-pull] scraper running, skip kickstart (cycle kế tiếp tự apply)"
    exit 0
  fi

  echo "[auto-pull] kickstart $SCRAPER_LABEL"
  launchctl kickstart "gui/$(id -u)/$SCRAPER_LABEL" 2>&1 || echo "[auto-pull] kickstart failed"
} >> "$LOG_FILE" 2>&1
