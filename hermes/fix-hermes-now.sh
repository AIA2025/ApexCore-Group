#!/bin/bash
# One-shot fix for hermes-agent LiteLLM proxy.
# Handles bind-mounted config files (writes to host path directly).
# Run on VPS: bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/clever-heisenberg-oi9673/hermes/fix-hermes-now.sh)

set -euo pipefail

CONTAINER="hermes-agent"
BRANCH="claude/clever-heisenberg-oi9673"
RAW="https://raw.githubusercontent.com/AIA2025/ApexCore-Group/${BRANCH}"
TMP="/tmp/litellm-fix-$$.yaml"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
h()    { echo -e "\n${BOLD}▶ $1${NC}"; }

echo -e "${BOLD}╔══════════════════════════════════════════╗"
echo    "║  Hermes LiteLLM Fix — OpenRouter Routing ║"
echo -e "╚══════════════════════════════════════════╝${NC}"

# ── 1. Container check ────────────────────────────────────────────────────────
h "1) Container check"
docker inspect "$CONTAINER" &>/dev/null || err "Container '$CONTAINER' not running"
ok "$CONTAINER is running"

# ── 2. API key check ──────────────────────────────────────────────────────────
h "2) API key check"
if docker exec "$CONTAINER" env | grep -q "^OPENROUTER_API_KEY="; then
  ok "OPENROUTER_API_KEY set in container"
else
  err "OPENROUTER_API_KEY not found in container. Add it to /root/.apexcore.env and ensure it is passed to the container."
fi

# ── 3. Download fixed config ──────────────────────────────────────────────────
h "3) Download fixed config"
curl -fsSL "${RAW}/hermes/litellm-config.yaml" -o "$TMP"
grep -q "model_list" "$TMP" || err "Downloaded config invalid"
ok "Config downloaded ($(grep 'model_name' "$TMP" | wc -l) models)"
echo ""
grep "model_name:" "$TMP" | awk '{print "    →", $3}'
echo "  API key: os.environ/OPENROUTER_API_KEY"

# ── 4. Apply config (bind-mount aware) ───────────────────────────────────────
h "4) Apply config"

# Find host-side path for /app/config.yaml (bind mount or named volume source)
HOST_CONFIG=$(docker inspect "$CONTAINER" \
  --format '{{range .Mounts}}{{if eq .Destination "/app/config.yaml"}}{{.Source}}{{end}}{{end}}' \
  2>/dev/null || true)

if [ -n "$HOST_CONFIG" ]; then
  ok "Bind mount detected: $HOST_CONFIG"
  cp "$HOST_CONFIG" "${HOST_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null && ok "Backup saved" || true
  cp "$TMP" "$HOST_CONFIG"
  ok "Config written to host path → container will pick it up on restart"
else
  # No bind mount — try docker cp
  warn "No bind mount found, trying docker cp..."
  docker exec "$CONTAINER" cp /app/config.yaml /app/config.yaml.bak 2>/dev/null || true
  if docker cp "$TMP" "${CONTAINER}:/app/config.yaml" 2>/dev/null; then
    ok "Config copied into container"
  else
    err "docker cp failed and no bind mount found. Inspect manually: docker inspect $CONTAINER --format '{{json .Mounts}}'"
  fi
fi

rm -f "$TMP"

# ── 5. Restart ────────────────────────────────────────────────────────────────
h "5) Restart"
docker restart "$CONTAINER"
ok "Container restarted"

# ── 6. Verify ────────────────────────────────────────────────────────────────
h "6) Verify"
echo "  Waiting 8s for LiteLLM startup..."
sleep 8

echo ""
echo "  Startup log:"
docker logs "$CONTAINER" 2>&1 | grep -iE "Proxy initialized|Set models:|openrouter|ProxyModel|Exception" | tail -10 | sed 's/^/    /'

echo ""
echo "  Active models in container config:"
docker exec "$CONTAINER" grep "model_name:" /app/config.yaml 2>/dev/null | awk '{print "    →", $3}' || true

echo ""
echo "  Quick smoke test (model=hermes-default):"
PROXY_PORT=$(docker port "$CONTAINER" 8000 2>/dev/null | head -1 | cut -d: -f2 || echo "18789")
RESP=$(curl -sf -m 15 \
  -X POST "http://localhost:${PROXY_PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-default","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  2>/dev/null || echo "FAILED")

if echo "$RESP" | grep -q '"choices"'; then
  ok "Proxy responding — OpenRouter routing confirmed"
elif echo "$RESP" | grep -q "FAILED"; then
  warn "No response on port ${PROXY_PORT}. Try: docker port $CONTAINER"
else
  warn "Response: $(echo "$RESP" | head -c 300)"
fi

echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════╗"
echo    "║  Fix complete. LiteLLM → OpenRouter       ║"
echo    "║  Models: hermes-default, claude-sonnet,   ║"
echo    "║          claude-opus, kimi, auto           ║"
echo -e "╚═══════════════════════════════════════════╝${NC}"
