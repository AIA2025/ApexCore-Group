#!/bin/bash
# Fix Telegram token in the Hermes Gateway container.
# Usage: bash hermes/fix-telegram.sh <NEW_TOKEN>
# Or:    TELEGRAM_TOKEN=xxx bash hermes/fix-telegram.sh

set -euo pipefail

CONTAINER="hermes-webui-cxlp-hermes-agent-1"
CONFIG_PATH="/home/hermes/.hermes/config.yaml"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
h()    { echo -e "\n${BOLD}▶ $1${NC}"; }

TOKEN="${1:-${TELEGRAM_TOKEN:-}}"
[ -z "$TOKEN" ] && err "Usage: $0 <telegram_bot_token>  OR  TELEGRAM_TOKEN=... $0"

echo -e "${BOLD}╔════════════════════════════════════════╗"
echo    "║  Hermes Gateway — Telegram Token Fix   ║"
echo -e "╚════════════════════════════════════════╝${NC}"

h "1) Container check"
docker inspect "$CONTAINER" &>/dev/null || err "Container '$CONTAINER' not running"
ok "$CONTAINER is running"

h "2) Backup config"
docker exec "$CONTAINER" cp "$CONFIG_PATH" "${CONFIG_PATH}.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null \
  && ok "Backup saved" || warn "Backup failed (non-fatal)"

h "3) Update token"
# Find and replace the old token line (any token value after 'token:')
docker exec "$CONTAINER" sh -c \
  "sed -i 's|token:.*|token: \"${TOKEN}\"|' ${CONFIG_PATH}"
ok "Token updated in config"

h "4) Verify"
echo "  Current token line in config:"
docker exec "$CONTAINER" grep -i "token\|bot_token\|api_token" "$CONFIG_PATH" 2>/dev/null \
  | sed 's/\(.\{20\}\).*/\1***/' || warn "No token line found — check field name manually"

h "5) Restart gateway"
docker restart "$CONTAINER"
ok "Container restarted"

echo "  Waiting 8s..."
sleep 8

h "6) Check Telegram connection"
docker logs "$CONTAINER" 2>&1 | grep -iE "telegram|platform|connected|failed|error" | tail -10 | sed 's/^/  /'

echo ""
echo -e "${GREEN}${BOLD}Done — check above for 'telegram connected' or similar.${NC}"
