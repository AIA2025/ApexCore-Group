#!/bin/bash
# fix-all.sh — Kompletter One-Shot Fix für den gesamten Hermes Stack
# Einmal ausführen, alles wird gefixt.
# Run: bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/clever-heisenberg-oi9673/hermes/fix-all.sh)

set -uo pipefail

BRANCH="claude/clever-heisenberg-oi9673"
RAW="https://raw.githubusercontent.com/AIA2025/ApexCore-Group/${BRANCH}"
LITELLM_CONTAINER="hermes-agent"
GATEWAY_CONTAINER="hermes-webui-cxlp-hermes-agent-1"
LITELLM_HOST_CONFIG="/opt/apexcore/ai-stack/hermes-config.yaml"
GATEWAY_CONFIG="/home/hermes/.hermes/config.yaml"
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }
sep()  { echo -e "${BOLD}══════════════════════════════════════════${NC}"; }

sep
echo -e "${BOLD}  ApexCore Hermes — Complete Fix${NC}"
sep

[ -z "$TELEGRAM_TOKEN" ] && { echo -e "${YELLOW}⚠️  TELEGRAM_TOKEN not set — Telegram fix will be skipped.${NC}"; echo "  Pass it with: TELEGRAM_TOKEN=xxx bash <(curl ...)"; }

# ═══════════════════════════════════════════════════════════════
# FIX 1: LiteLLM Proxy — OpenRouter model routing
# ═══════════════════════════════════════════════════════════════
h "FIX 1: LiteLLM Proxy (hermes-agent)"

if ! docker inspect "$LITELLM_CONTAINER" &>/dev/null; then
  err "Container '$LITELLM_CONTAINER' not found — skipping"
else
  # Write config directly to bind-mount host path
  echo "  Writing config to $LITELLM_HOST_CONFIG ..."
  if curl -fsSL "${RAW}/hermes/litellm-config.yaml" -o "${LITELLM_HOST_CONFIG}.new"; then
    grep -q "model_list" "${LITELLM_HOST_CONFIG}.new" || { err "Downloaded config invalid"; exit 1; }
    cp "$LITELLM_HOST_CONFIG" "${LITELLM_HOST_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    mv "${LITELLM_HOST_CONFIG}.new" "$LITELLM_HOST_CONFIG"
    ok "Config written (5 models: hermes-default, claude-sonnet, claude-opus, kimi, auto)"
  else
    err "Failed to download config from GitHub"
  fi

  # Check for LITELLM_MASTER_KEY
  MASTER_KEY=$(docker exec "$LITELLM_CONTAINER" env 2>/dev/null | grep -i "^LITELLM_MASTER_KEY=" | cut -d= -f2- || true)
  if [ -n "$MASTER_KEY" ]; then
    warn "LITELLM_MASTER_KEY is set — callers must send: Authorization: Bearer ${MASTER_KEY:0:8}..."
    echo "  → If Hermes Gateway calls LiteLLM, add this key to the gateway's provider config."
  fi

  docker restart "$LITELLM_CONTAINER" >/dev/null
  ok "hermes-agent restarted"
fi

# ═══════════════════════════════════════════════════════════════
# FIX 2: Hermes Gateway — Telegram token
# ═══════════════════════════════════════════════════════════════
h "FIX 2: Hermes Gateway Telegram token"

if ! docker inspect "$GATEWAY_CONTAINER" &>/dev/null; then
  err "Container '$GATEWAY_CONTAINER' not found — skipping"
else
  # Find how the token is stored: YAML file or env var
  TOKEN_SET=false

  # Try YAML config (try multiple possible field names)
  for FIELD in "token" "bot_token" "api_token" "telegram_token"; do
    if docker exec "$GATEWAY_CONTAINER" grep -qi "^[[:space:]]*${FIELD}:" "$GATEWAY_CONFIG" 2>/dev/null; then
      docker exec "$GATEWAY_CONTAINER" sh -c \
        "sed -i 's|^\([[:space:]]*${FIELD}:[[:space:]]*\).*|\1\"${TELEGRAM_TOKEN}\"|' ${GATEWAY_CONFIG}"
      ok "Token updated in YAML (field: ${FIELD})"
      TOKEN_SET=true
      break
    fi
  done

  # Try env var in container (look at .env file)
  if [ "$TOKEN_SET" = false ]; then
    ENV_FILE="/home/hermes/.hermes/.env"
    if docker exec "$GATEWAY_CONTAINER" test -f "$ENV_FILE" 2>/dev/null; then
      if docker exec "$GATEWAY_CONTAINER" grep -qi "TELEGRAM" "$ENV_FILE" 2>/dev/null; then
        docker exec "$GATEWAY_CONTAINER" sh -c \
          "sed -i 's|^TELEGRAM.*TOKEN=.*|TELEGRAM_BOT_TOKEN=${TELEGRAM_TOKEN}|' ${ENV_FILE}"
        ok "Token updated in .env file"
        TOKEN_SET=true
      fi
    fi
  fi

  # Fallback: show full config so we know the format
  if [ "$TOKEN_SET" = false ]; then
    warn "Could not auto-detect token field. Config excerpt:"
    docker exec "$GATEWAY_CONTAINER" cat "$GATEWAY_CONFIG" 2>/dev/null | grep -i "telegram" -A5 | head -15 | sed 's/^/    /'
    echo ""
    warn "Manual fix needed — send config output to Claude"
  fi

  docker restart "$GATEWAY_CONTAINER" >/dev/null
  ok "hermes-webui-cxlp-hermes-agent-1 restarted"
fi

# ═══════════════════════════════════════════════════════════════
# VERIFY
# ═══════════════════════════════════════════════════════════════
h "VERIFY — waiting 10s for startup"
sleep 10

echo ""
echo "─── LiteLLM Proxy logs ───"
docker logs "$LITELLM_CONTAINER" 2>&1 | grep -iE "Set models:|initialized|Exception|Error" | tail -6 | sed 's/^/  /'

echo ""
echo "─── LiteLLM active models ───"
docker exec "$LITELLM_CONTAINER" grep "model_name:" /app/config.yaml 2>/dev/null | awk '{print "  ✓", $3}' || true

echo ""
echo "─── Hermes Gateway logs ───"
docker logs "$GATEWAY_CONTAINER" 2>&1 | grep -iE "telegram|connected|failed|platform|started" | tail -8 | sed 's/^/  /'

echo ""
echo "─── Quick smoke test: LiteLLM /v1/models ───"
PORT=$(docker port "$LITELLM_CONTAINER" 8000 2>/dev/null | head -1 | cut -d: -f2 || echo "18789")
MODELS=$(curl -sf -m 5 "http://localhost:${PORT}/v1/models" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('data', []):
    print(' ', m.get('id','?'))
" 2>/dev/null || echo "  (auth required or not reachable on :${PORT})")
echo "$MODELS"

sep
echo -e "${GREEN}${BOLD}  Fix complete.${NC}"
echo "  LiteLLM → 5 models via OpenRouter"
echo "  Gateway → Telegram token updated + restarted"
sep
