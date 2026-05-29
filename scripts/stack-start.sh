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

# Networks are created by docker compose with the correct labels.
# Do NOT pre-create with docker network create — that produces label-less networks
# which docker compose then rejects with "incorrect label" errors.

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
