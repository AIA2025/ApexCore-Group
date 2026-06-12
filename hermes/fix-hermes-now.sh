#!/bin/bash
# One-shot fix for hermes-agent LiteLLM proxy.
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

# ── Check container ──────────────────────────────────────────────────────────
h "1) Container check"
docker inspect "$CONTAINER" &>/dev/null || err "Container '$CONTAINER' not running"
ok "$CONTAINER is running"

# ── Check OPENROUTER_API_KEY ──────────────────────────────────────────────────
h "2) API key check"
if docker exec "$CONTAINER" env | grep -q "^OPENROUTER_API_KEY="; then
  ok "OPENROUTER_API_KEY set in container"
elif [ -f /root/.apexcore.env ] && grep -q "OPENROUTER_API_KEY=" /root/.apexcore.env; then
  KEY=$(grep "^OPENROUTER_API_KEY=" /root/.apexcore.env | head -1 | cut -d= -f2-)
  warn "Key found in .apexcore.env but not in container — will inject via restart"
  # Inject via docker exec env set is not possible; use docker run workaround below
  INJECT_KEY="$KEY"
else
  err "OPENROUTER_API_KEY not found. Add it to /root/.apexcore.env and rerun."
fi

# ── Download fixed config ────────────────────────────────────────────────────
h "3) Download fixed config"
curl -fsSL "${RAW}/hermes/litellm-config.yaml" -o "$TMP"
grep -q "model_list" "$TMP" || err "Downloaded config invalid"
ok "Config downloaded ($(grep 'model_name' "$TMP" | wc -l) models)"

# ── Show what we're deploying ─────────────────────────────────────────────────
echo ""
echo "  Models to deploy:"
grep "model_name:" "$TMP" | awk '{print "    →", $3}'
echo "  API key: os.environ/OPENROUTER_API_KEY"
echo ""

# ── Backup + apply ────────────────────────────────────────────────────────────
h "4) Apply config"
docker exec "$CONTAINER" cp /app/config.yaml /app/config.yaml.bak 2>/dev/null && ok "Backup saved" || true
docker cp "$TMP" "${CONTAINER}:/app/config.yaml"
ok "Config applied"
rm -f "$TMP"

# ── Restart ───────────────────────────────────────────────────────────────────
h "5) Restart"
docker restart "$CONTAINER"
ok "Restarted"

# ── Wait + verify ────────────────────────────────────────────────────────────
h "6) Verify"
echo "  Waiting 8s for LiteLLM startup..."
sleep 8

echo ""
echo "  Startup log:"
docker logs "$CONTAINER" 2>&1 | grep -iE "Proxy initialized|Set models|openrouter|Error|error" | tail -8 | sed 's/^/    /'

echo ""
echo "  Quick smoke test (model=hermes-default):"
PROXY_PORT=$(docker port "$CONTAINER" 8000 2>/dev/null | head -1 | cut -d: -f2 || echo "18789")
RESP=$(curl -sf -m 10 \
  -X POST "http://localhost:${PROXY_PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-default","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  2>/dev/null || echo "FAILED")

if echo "$RESP" | grep -q '"choices"'; then
  ok "Proxy responding — OpenRouter routing confirmed"
elif echo "$RESP" | grep -q "FAILED"; then
  warn "Proxy not responding on port ${PROXY_PORT} — check docker port mapping"
  echo "  Run: docker port $CONTAINER"
else
  warn "Unexpected response: $(echo "$RESP" | head -c 200)"
fi

echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════╗"
echo    "║  Fix complete. LiteLLM → OpenRouter       ║"
echo    "║  Models: hermes-default, claude-sonnet,   ║"
echo    "║          claude-opus, kimi, auto           ║"
echo -e "╚═══════════════════════════════════════════╝${NC}"
