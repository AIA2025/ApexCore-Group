#!/usr/bin/env bash
# stack-stop.sh — Stop all ApexCore stacks (reverse start order)
#
# Usage: /srv/apexcore/scripts/stack-stop.sh [--volumes]
# --volumes: also remove named volumes (DESTRUCTIVE — data loss!)

set -euo pipefail

APEXCORE_DIR="/srv/apexcore"
REMOVE_VOLUMES=""

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

[ -d "$APEXCORE_DIR" ] || die "$APEXCORE_DIR not found"
cd "$APEXCORE_DIR"

if [ "${1:-}" = "--volumes" ]; then
  echo "WARNING: --volumes flag will DELETE all named volumes (n8n_data, open_webui_data, etc.)"
  echo "Press Ctrl+C within 5 seconds to abort..."
  sleep 5
  REMOVE_VOLUMES="-v"
fi

log "=== ApexCore Stack Stop ==="

docker compose -f infra-compose/docker-compose.yml down $REMOVE_VOLUMES || true
log "infra-compose: stopped"

docker compose -f automation-stack/docker-compose.yml down $REMOVE_VOLUMES || true
log "automation-stack: stopped"

docker compose -f ai-stack/docker-compose.yml down $REMOVE_VOLUMES || true
log "ai-stack: stopped"

log "=== All stacks stopped ==="
[ -n "$REMOVE_VOLUMES" ] && log "WARNING: Volumes were removed."
