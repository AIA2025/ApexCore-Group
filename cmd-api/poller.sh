#!/usr/bin/env bash
# poller.sh — Pull-based deploy agent for ApexCore VPS
# Runs as a systemd timer every 2 minutes. Checks GitHub for new commits
# on the tracked branch; if SHA changed, calls local cmd-api /deploy.
# Zero inbound connections required — VPS pulls, never gets pushed to.
set -euo pipefail

STATE_FILE="/var/lib/apexcore-poller/last_sha"
BRANCH_FILE="/var/lib/apexcore-poller/branch"
LOG="/var/log/apexcore-poller.log"
CMD_API="http://127.0.0.1:7070"
REPO="AIA2025/ApexCore-Group"

mkdir -p "$(dirname "$STATE_FILE")"
exec >> "$LOG" 2>&1

BRANCH="${1:-$(cat "$BRANCH_FILE" 2>/dev/null || echo "main")}"
echo "$BRANCH" > "$BRANCH_FILE"

# Fetch latest SHA from GitHub API (no auth needed for public repo)
LATEST=$(curl -sf "https://api.github.com/repos/${REPO}/commits/${BRANCH}" \
  -H "Accept: application/vnd.github.v3+json" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'][:12])" 2>/dev/null || echo "")

if [[ -z "$LATEST" ]]; then
  echo "[$(date -u +%FT%TZ)] Could not fetch SHA for ${BRANCH} — skipping"
  exit 0
fi

LAST=$(cat "$STATE_FILE" 2>/dev/null || echo "")

if [[ "$LATEST" == "$LAST" ]]; then
  exit 0  # No change
fi

echo "[$(date -u +%FT%TZ)] New commit detected: ${LAST:-none} → ${LATEST} on ${BRANCH}"
echo "$LATEST" > "$STATE_FILE"

# Check cmd-api is running
if ! curl -sf --connect-timeout 3 "${CMD_API}/health" >/dev/null; then
  echo "[$(date -u +%FT%TZ)] cmd-api not running — skipping deploy"
  exit 1
fi

# Trigger deploy
HTTP=$(curl -sf -o /tmp/poller-resp.json -w "%{http_code}" \
  -X POST "${CMD_API}/deploy" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${CMD_TOKEN:-}" \
  -d "{\"branch\":\"${BRANCH}\"}" \
  --connect-timeout 5 --max-time 10 || echo "000")

echo "[$(date -u +%FT%TZ)] Deploy triggered: HTTP ${HTTP} — $(cat /tmp/poller-resp.json 2>/dev/null)"
