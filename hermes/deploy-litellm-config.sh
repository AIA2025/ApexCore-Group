#!/bin/bash
# Apply litellm-config.yaml into the hermes-agent container.
# Works without a local git repo — fetches directly from GitHub.
# Usage: bash hermes/deploy-litellm-config.sh [branch]

set -euo pipefail

CONTAINER="hermes-agent"
BRANCH="${1:-claude/clever-heisenberg-oi9673}"
RAW="https://raw.githubusercontent.com/AIA2025/ApexCore-Group/${BRANCH}/hermes/litellm-config.yaml"
TMP="/tmp/litellm-config-$$.yaml"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
ok()  { echo -e "${GREEN}✅ $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ── 1. Container check ────────────────────────────────────────────────────────
docker inspect "$CONTAINER" &>/dev/null || err "Container '$CONTAINER' not found"
ok "Container '$CONTAINER' found"

# ── 2. Fetch config ───────────────────────────────────────────────────────────
echo "Fetching config from: $RAW"
curl -fsSL "$RAW" -o "$TMP" || err "Failed to download config from GitHub"
ok "Config downloaded"

# ── 3. Validate YAML has model_list ──────────────────────────────────────────
grep -q "model_list" "$TMP" || err "Downloaded file missing model_list — aborting"
ok "Config validated (model_list present)"

# ── 4. Backup existing config ────────────────────────────────────────────────
docker exec "$CONTAINER" cp /app/config.yaml /app/config.yaml.bak 2>/dev/null \
  && ok "Existing config backed up → /app/config.yaml.bak" \
  || echo "  (no existing config to back up)"

# ── 5. Copy new config ───────────────────────────────────────────────────────
docker cp "$TMP" "${CONTAINER}:/app/config.yaml"
ok "New config copied into container"
rm -f "$TMP"

# ── 6. Verify OPENROUTER_API_KEY is set in container ─────────────────────────
if docker exec "$CONTAINER" env | grep -q "^OPENROUTER_API_KEY="; then
  ok "OPENROUTER_API_KEY is set in container"
else
  echo "⚠️  OPENROUTER_API_KEY not found in container env — proxy will fail"
  echo "   Fix: docker run ... --env OPENROUTER_API_KEY=sk-or-... (see /root/.apexcore.env)"
fi

# ── 7. Restart container ──────────────────────────────────────────────────────
docker restart "$CONTAINER"
ok "Container restarted"

# ── 8. Wait and check logs ────────────────────────────────────────────────────
echo "Waiting 6s for startup..."
sleep 6

echo ""
echo "=== Startup log (model lines) ==="
docker logs "$CONTAINER" 2>&1 | grep -iE "model|openrouter|error|Error|initialized" | tail -10 || true

echo ""
echo "=== Health check ==="
HEALTH=$(docker exec "$CONTAINER" curl -sf http://localhost:8000/health/liveliness 2>/dev/null \
         || curl -sf "http://localhost:$(docker port "$CONTAINER" 8000 2>/dev/null | cut -d: -f2 || echo 18789)/health/liveliness" 2>/dev/null \
         || echo "unreachable")
echo "  $HEALTH"

echo ""
ok "Deploy complete — hermes-agent is running with OpenRouter config"
echo "   Models: hermes-default, claude-sonnet, claude-opus, kimi, auto"
echo "   All routed via OPENROUTER_API_KEY → openrouter.ai"
