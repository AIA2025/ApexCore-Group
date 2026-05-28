#!/usr/bin/env bash
# healthcheck.sh — Check status of all ApexCore containers
# Usage: /srv/apexcore/scripts/healthcheck.sh
# Run on the VPS as root

set -uo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GREY='\033[0;37m'
NC='\033[0m'

ok()   { printf "  ${GREEN}✓${NC} %-20s %s\n" "$1" "$2"; }
warn() { printf "  ${YELLOW}⚠${NC} %-20s %s\n" "$1" "$2"; }
fail() { printf "  ${RED}✗${NC} %-20s %s\n" "$1" "$2"; }
info() { printf "  ${GREY}·${NC} %-20s %s\n" "$1" "$2"; }

check() {
  local name=$1
  local http_path=${2:-}
  if ! docker inspect "$name" &>/dev/null; then
    fail "$name" "(not found)"
    return
  fi
  local state
  state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null)
  if [ "$state" != "running" ]; then
    fail "$name" "(state: $state)"
    return
  fi
  if [ -z "$http_path" ]; then
    ok "$name" "(running)"
    return
  fi
  # HTTP check inside container
  if docker exec "$name" wget -qO- "$http_path" >/dev/null 2>&1 \
  || docker exec "$name" curl -sf "$http_path" >/dev/null 2>&1; then
    ok "$name" "(running, HTTP ok)"
  else
    warn "$name" "(running, HTTP not ready yet)"
  fi
}

echo ""
echo "═══════════════════════════════════════"
echo " ApexCore Health Check — $(date '+%H:%M:%S')"
echo "═══════════════════════════════════════"

echo ""
echo "── Infra ────────────────────────────"
check "caddy" "http://localhost:80"

echo ""
echo "── AI Stack ─────────────────────────"
check "open-webui"   "http://localhost:8080/health"
check "hermes-agent" "http://localhost:4000/health"
check "hermes-webui" ""
check "ollama"       "http://localhost:11434/"
check "openclaw"     ""

echo ""
echo "── Automation Stack ─────────────────"
check "n8n" "http://localhost:5678/healthz"

echo ""
echo "── Compose Status ───────────────────"
for f in infra-compose/docker-compose.yml ai-stack/docker-compose.yml automation-stack/docker-compose.yml; do
  if [ -f "/srv/apexcore/$f" ]; then
    docker compose -f "/srv/apexcore/$f" ps --format "  {{.Name}}\t{{.Status}}" 2>/dev/null || true
  fi
done

echo ""
echo "── Endpoints ────────────────────────"
for url in \
  "https://ai.apexcore.group" \
  "https://hermes.apexcore.group" \
  "https://n8n.apexcore.group" \
  "https://ops.apexcore.group" \
  "https://dashboard.apexcore.group"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "err")
  if [[ "$code" =~ ^[23] ]]; then
    ok "$url" "(HTTP $code)"
  else
    warn "$url" "(HTTP $code)"
  fi
done

echo ""
