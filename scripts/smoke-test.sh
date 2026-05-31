#!/usr/bin/env bash
# smoke-test.sh — Quick validation of all ApexCore V1 services
#
# Usage: /srv/apexcore/scripts/smoke-test.sh
# Run as: root on the VPS (reads .env.dispatcher for DISPATCHER_TOKEN)

set -euo pipefail

APEXCORE_DIR="/srv/apexcore"
PASS=0; FAIL=0

ok()   { echo "  ✅ $*"; ((PASS++)); }
fail() { echo "  ❌ $*"; ((FAIL++)); }
sep()  { echo ""; echo "── $* ──────────────────────────────────────────────"; }

# Load dispatcher token if available
if [ -f "$APEXCORE_DIR/cmd-api/.env.dispatcher" ]; then
  set -a; source "$APEXCORE_DIR/cmd-api/.env.dispatcher"; set +a
fi
DISPATCHER_TOKEN="${DISPATCHER_TOKEN:-}"

echo "=== ApexCore Smoke Test ==="
echo "$(date '+%Y-%m-%d %H:%M:%S') on $(hostname)"

# ── 1. Container health ───────────────────────────────────────────────────────
sep "Container Status"
for svc in hermes-agent open-webui hermes-webui n8n ollama; do
  if docker inspect "$svc" --format '{{.State.Status}}' 2>/dev/null | grep -q "running"; then
    ok "$svc: running"
  else
    fail "$svc: not running"
  fi
done

# ── 2. Service ports ──────────────────────────────────────────────────────────
sep "Port Checks"
check_port() {
  local label=$1 port=$2
  if nc -z 127.0.0.1 "$port" 2>/dev/null; then
    ok "$label (127.0.0.1:$port)"
  else
    fail "$label (127.0.0.1:$port) — not listening"
  fi
}
check_port "hermes-agent"  4000
check_port "open-webui"    3000
check_port "hermes-webui"  3001
check_port "n8n"           5678
check_port "dispatcher"    7071
check_port "cmd-api"       7070

# ── 3. Dispatcher health ──────────────────────────────────────────────────────
sep "Dispatcher"
HEALTH=$(curl -sf http://localhost:7071/health 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"ok"'; then
  ok "GET /health → ok"
else
  fail "GET /health → $HEALTH"
fi

if [ -n "$DISPATCHER_TOKEN" ]; then
  ROUTES=$(curl -sf http://localhost:7071/routes \
    -H "Authorization: Bearer $DISPATCHER_TOKEN" 2>/dev/null || echo "FAIL")
  if echo "$ROUTES" | grep -q "RESEARCH"; then
    ok "GET /routes → routing table present"
  else
    fail "GET /routes → $ROUTES"
  fi

  DISPATCH=$(curl -sf -X POST http://localhost:7071/dispatch \
    -H "Authorization: Bearer $DISPATCHER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"task": "Research: what is Bitcoin?"}' 2>/dev/null || echo "FAIL")
  if echo "$DISPATCH" | grep -q '"status"'; then
    STATUS=$(echo "$DISPATCH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","?"))' 2>/dev/null || echo "?")
    INTENT=$(echo "$DISPATCH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("intent","?"))' 2>/dev/null || echo "?")
    ok "POST /dispatch → status=$STATUS intent=$INTENT"
  else
    fail "POST /dispatch → $DISPATCH"
  fi
else
  echo "  ⚠️  DISPATCHER_TOKEN not set — skipping authenticated tests"
  echo "     Source: $APEXCORE_DIR/cmd-api/.env.dispatcher"
fi

# ── 4. Hermes agent ───────────────────────────────────────────────────────────
sep "Hermes Agent (LiteLLM)"
if curl -sf http://localhost:4000/health/liveliness >/dev/null 2>&1; then
  ok "GET /health/liveliness → alive"
else
  fail "GET /health/liveliness"
fi

# ── 5. n8n ────────────────────────────────────────────────────────────────────
sep "n8n"
if curl -sf http://localhost:5678/healthz >/dev/null 2>&1; then
  ok "GET /healthz → ok"
else
  fail "GET /healthz"
fi

# ── 6. nginx ──────────────────────────────────────────────────────────────────
sep "nginx"
if nginx -t 2>&1 | grep -q "test is successful"; then
  ok "nginx config valid"
else
  fail "nginx config invalid — run: nginx -t"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  echo "  ✅ All $TOTAL checks passed"
else
  echo "  ✅ $PASS passed  ❌ $FAIL failed  (total: $TOTAL)"
fi
echo "═══════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ]
