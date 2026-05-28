#!/usr/bin/env bash
# stack-start.sh — Start all ApexCore stacks in correct dependency order
#
# Order matters:
#   1. ai-stack     — creates ai_net (required by automation-stack + infra-compose)
#   2. automation-stack — creates automation_net (required by infra-compose)
#   3. infra-compose    — Caddy joins both external networks; must start last
#
# --remove-orphans cleans up containers from renamed/removed services
#
# Usage: /srv/apexcore/scripts/stack-start.sh
# Run as: root on the VPS

set -euo pipefail

APEXCORE_DIR="/srv/apexcore"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }
step() { echo ""; echo "── $* ──────────────────────────────────────────────"; }

[ -d "$APEXCORE_DIR" ] || die "$APEXCORE_DIR not found — is this running on the VPS?"
cd "$APEXCORE_DIR"

log "=== ApexCore Stack Start ==="

# Pre-create external networks so Caddy can join them before stacks fully start.
# docker compose will also create them, but doing it upfront avoids race conditions
# if stacks are started in parallel externally.
step "Networks"
for net in ai_net automation_net; do
  if docker network inspect "$net" &>/dev/null 2>&1; then
    log "  network exists: $net"
  else
    log "  creating network: $net"
    docker network create "$net"
  fi
done

# 1. AI Stack (creates ai_net, starts open-webui, hermes-agent, ollama)
step "ai-stack"
docker compose -f ai-stack/docker-compose.yml up -d --remove-orphans
log "ai-stack: up"

# 2. Automation Stack (joins ai_net as external, creates automation_net, starts n8n)
step "automation-stack"
docker compose -f automation-stack/docker-compose.yml up -d --remove-orphans
log "automation-stack: up"

# 3. Infra / Caddy (joins ai_net + automation_net as external — must come last)
step "infra-compose (Caddy)"
docker compose -f infra-compose/docker-compose.yml up -d --remove-orphans
log "infra-compose: up"

echo ""
log "=== All stacks started ==="
log "Run: $APEXCORE_DIR/scripts/healthcheck.sh"
