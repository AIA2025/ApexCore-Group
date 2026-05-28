#!/usr/bin/env bash
# stack-stop.sh — Stop all ApexCore stacks (reverse order)
# Usage: /srv/apexcore/scripts/stack-stop.sh
set -euo pipefail

APEXCORE_DIR="/srv/apexcore"
cd "$APEXCORE_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== ApexCore Stack Stop ==="

log "Stopping infra-compose (Caddy)..."
docker compose -f infra-compose/docker-compose.yml down || true

log "Stopping automation-stack..."
docker compose -f automation-stack/docker-compose.yml down || true

log "Stopping ai-stack..."
docker compose -f ai-stack/docker-compose.yml down || true

log "=== All stacks stopped ==="
