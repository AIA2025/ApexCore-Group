#!/usr/bin/env bash
# healthcheck.sh — ApexCore service health check
#
# Checks container state + HTTP liveness for each service.
# Run on the VPS as root.
#
# Usage: /srv/apexcore/scripts/healthcheck.sh

set -uo pipefail

APEXCORE_DIR="/srv/apexcore"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { printf "  ${GREEN}✓${NC}  %-22s %s\n" "$1" "$2"; }
warn() { printf "  ${YELLOW}⚠${NC}  %-22s %s\n" "$1" "$2"; }
fail() { printf "  ${RED}✗${NC}  %-22s %s\n" "$1" "$2"; }

check_container() {
  local name=$1
  local http_url=${2:-}

  if ! docker inspect "$name" &>/dev/null 2>&1; then
    fail "$name" "not found"
    return
  fi

  local state
  state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null)
  if [ "$state" != "running" ]; then
    fail "$name" "state: $state"
    return
  fi

  if [ -z "$http_url" ]; then
    ok "$name" "running"
    return
  fi

  # HTTP check executed inside the container (avoids host-port dependency)
  if docker exec "$name" sh -c "wget -qO- '$http_url' >/dev/null 2>&1 || curl -sf '$http_url' >/dev/null 2>&1"; then
    ok "$name" "running  HTTP ✓"
  else
    warn "$name" "running  HTTP not ready"
  fi
}

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ApexCore Health Check  —  $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════"

echo ""
echo "── Infra ──────────────────────────────────────────"
check_container "caddy" "http://localhost:80"

echo ""
echo "── AI Stack ───────────────────────────────────────"
check_container "open-webui"   "http://localhost:8080/health"
check_container "hermes-agent" "http://localhost:4000/health"
check_container "hermes-webui" "http://localhost:8080/health"
check_container "ollama"       "http://localhost:11434/"
check_container "openclaw"     ""

echo ""
echo "── Automation Stack ───────────────────────────────"
check_container "n8n" "http://localhost:5678/healthz"

echo ""
echo "── Compose Service Status ─────────────────────────"
for stack in infra-compose ai-stack automation-stack; do
  f="$APEXCORE_DIR/$stack/docker-compose.yml"
  [ -f "$f" ] && \
    docker compose -f "$f" ps --format "  {{.Name}}\t{{.Status}}" 2>/dev/null || true
done

echo ""
echo "── External Endpoints ─────────────────────────────"
for entry in \
  "ai.apexcore.group" \
  "hermes.apexcore.group" \
  "n8n.apexcore.group" \
  "ops.apexcore.group" \
  "dashboard.apexcore.group"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "https://$entry" 2>/dev/null || echo "err")
  if [[ "$code" =~ ^[23] ]]; then
    ok "https://$entry" "HTTP $code"
  else
    warn "https://$entry" "HTTP $code"
  fi
done

echo ""
