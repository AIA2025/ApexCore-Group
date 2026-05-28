#!/usr/bin/env bash
# stack-start.sh — Start all ApexCore stacks in correct order
# Usage: /srv/apexcore/scripts/stack-start.sh
set -euo pipefail

APEXCORE_DIR="/srv/apexcore"
cd "$APEXCORE_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

[ -d "$APEXCORE_DIR" ] || die "$APEXCORE_DIR not found"

log "=== ApexCore Stack Start ==="

# Pre-create external networks so Caddy can join them even if stacks aren't up yet
for net in ai_net automation_net; do
  if ! docker network inspect "$net" &>/dev/null; then
    log "Creating network: $net"
    docker network create "$net"
  else
    log "Network exists: $net"
  fi
done

# 1. AI Stack — creates ai_net
log "Starting ai-stack..."
docker compose -f ai-stack/docker-compose.yml up -d
log "ai-stack: started"

# 2. Automation Stack — creates automation_net
log "Starting automation-stack..."
docker compose -f automation-stack/docker-compose.yml up -d
log "automation-stack: started"

# 3. Infra (Caddy) — joins both external networks; must start last
log "Starting infra-compose (Caddy)..."
docker compose -f infra-compose/docker-compose.yml up -d
log "infra-compose: started"

log "=== All stacks started. Run ./scripts/healthcheck.sh to verify. ==="
