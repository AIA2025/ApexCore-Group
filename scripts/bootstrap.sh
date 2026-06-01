#!/usr/bin/env bash
# bootstrap.sh — ApexCore V1 full recovery / first-time setup
#
# Run from Hostinger VPS console (root):
#   bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/main/scripts/bootstrap.sh)
# Or from the repo:
#   /srv/apexcore/scripts/bootstrap.sh
#
# Safe to re-run: never overwrites existing .env files or API keys.

set -euo pipefail
APEXCORE_DIR="/srv/apexcore"
BRANCH="${APEXCORE_BRANCH:-main}"
LOG="/var/log/apexcore-bootstrap.log"

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
ok()   { echo "  ✅ $*"; }
warn() { echo "  ⚠️  $*"; }
fail() { echo "  ❌ $*"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ApexCore V1 Bootstrap / Recovery            ║"
echo "╚══════════════════════════════════════════════╝"
echo "Branch: $BRANCH  |  $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── 1. Disk space guard ───────────────────────────────────────────────────────
log "Checking disk space..."
DISK_PCT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
  warn "Disk at ${DISK_PCT}% — running cleanup first"
  docker system prune -f --volumes=false 2>/dev/null || true
  journalctl --vacuum-size=200M 2>/dev/null || true
  find /var/log -name "*.log" -size +100M -exec truncate -s 50M {} \; 2>/dev/null || true
  DISK_PCT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
  log "Disk after cleanup: ${DISK_PCT}%"
fi
[ "$DISK_PCT" -lt 98 ] && ok "Disk: ${DISK_PCT}%" || warn "Disk still at ${DISK_PCT}% — monitor closely"

# ── 2. Git pull ───────────────────────────────────────────────────────────────
log "Pulling latest code..."
if [ -d "$APEXCORE_DIR/.git" ]; then
  git -C "$APEXCORE_DIR" stash push -m "bootstrap-$(date +%s)" 2>/dev/null || true
  git -C "$APEXCORE_DIR" fetch origin
  git -C "$APEXCORE_DIR" checkout "$BRANCH"
  git -C "$APEXCORE_DIR" pull origin "$BRANCH"
  ok "Code updated to $(git -C "$APEXCORE_DIR" rev-parse --short HEAD)"
else
  log "Cloning repo..."
  git clone https://github.com/AIA2025/ApexCore-Group.git "$APEXCORE_DIR"
  git -C "$APEXCORE_DIR" checkout "$BRANCH"
  ok "Repo cloned"
fi
chmod +x "$APEXCORE_DIR"/scripts/*.sh 2>/dev/null || true

# ── 3. Docker ─────────────────────────────────────────────────────────────────
log "Checking Docker..."
if ! systemctl is-active --quiet docker 2>/dev/null; then
  systemctl start docker
  sleep 3
fi
docker info &>/dev/null && ok "Docker running" || fail "Docker not running"

# ── 4. Networks & volumes ─────────────────────────────────────────────────────
log "Ensuring networks and volumes..."
for net in ai_net automation_net infra_net; do
  docker network inspect "$net" &>/dev/null \
    || docker network create "$net" \
    && ok "network: $net"
done
docker volume inspect n8n_data &>/dev/null \
  || docker volume create n8n_data \
  && ok "volume: n8n_data"

# ── 5. .env placeholder guard (never overwrites existing keys) ────────────────
log "Checking .env files..."
create_env_if_missing() {
  local path=$1 content=$2
  if [ ! -f "$path" ]; then
    mkdir -p "$(dirname "$path")"
    echo "$content" > "$path"
    warn "Created placeholder: $path — fill in real values"
  else
    ok "Exists (not touched): $path"
  fi
}
create_env_if_missing "$APEXCORE_DIR/ai-stack/.env" \
"OPENROUTER_API_KEY=REPLACE_ME
LITELLM_MASTER_KEY=REPLACE_ME"

create_env_if_missing "$APEXCORE_DIR/automation-stack/.env" \
"N8N_BASIC_AUTH_PASSWORD=REPLACE_ME
N8N_ENCRYPTION_KEY=REPLACE_ME
LITELLM_MASTER_KEY=REPLACE_ME
DISPATCHER_TOKEN=REPLACE_ME"

create_env_if_missing "$APEXCORE_DIR/cmd-api/.env.dispatcher" \
"DISPATCHER_TOKEN=REPLACE_ME
LITELLM_MASTER_KEY=REPLACE_ME
CMD_TOKEN=REPLACE_ME"

# ── 6. nginx vhost ────────────────────────────────────────────────────────────
log "Configuring nginx..."
VHOST_SRC="$APEXCORE_DIR/infra-compose/nginx-vhost.conf"
VHOST_DST="/etc/nginx/sites-available/apexcore.conf"
VHOST_LINK="/etc/nginx/sites-enabled/apexcore.conf"
if [ -f "$VHOST_SRC" ] && command -v nginx &>/dev/null; then
  cp "$VHOST_SRC" "$VHOST_DST"
  mkdir -p /etc/nginx/sites-enabled
  [ -L "$VHOST_LINK" ] || ln -sf "$VHOST_DST" "$VHOST_LINK"
  if nginx -t 2>&1 | grep -q "test is successful"; then
    nginx -s reload && ok "nginx: vhost loaded + reloaded"
  else
    warn "nginx -t failed — vhost not applied (check /etc/nginx/sites-available/apexcore.conf)"
  fi
fi

# ── 7. Static assets ──────────────────────────────────────────────────────────
mkdir -p /opt/apexcore-dashboard
[ -f "$APEXCORE_DIR/dashboard/index.html" ] \
  && cp "$APEXCORE_DIR/dashboard/index.html" /opt/apexcore-dashboard/index.html \
  && ok "Dashboard synced"

# ── 8. Docker Compose stacks ──────────────────────────────────────────────────
log "Starting compose stacks..."
for cf in \
  "ai-stack/docker-compose.yml" \
  "automation-stack/docker-compose.yml" \
  "infra-compose/docker-compose.yml"; do
  FULL="$APEXCORE_DIR/$cf"
  if [ -f "$FULL" ]; then
    docker compose -f "$FULL" up -d --remove-orphans 2>&1 \
      | tail -3 | sed 's/^/    /'
    ok "compose: $cf"
  else
    warn "Not found: $cf"
  fi
done

# ── 9. cmd-api ────────────────────────────────────────────────────────────────
log "Starting cmd-api..."
pkill -f "python3.*server.py" 2>/dev/null || true
sleep 1

# Load CMD_TOKEN from .env.dispatcher if not already set
if [ -z "${CMD_TOKEN:-}" ] && [ -f "$APEXCORE_DIR/cmd-api/.env.dispatcher" ]; then
  CMD_TOKEN=$(grep '^CMD_TOKEN=' "$APEXCORE_DIR/cmd-api/.env.dispatcher" | cut -d= -f2 | tr -d '"')
fi

if [ -z "${CMD_TOKEN:-}" ]; then
  warn "CMD_TOKEN not set — cmd-api will run WITHOUT auth (fix: set CMD_TOKEN in cmd-api/.env.dispatcher)"
fi

CMD_TOKEN="${CMD_TOKEN:-}" \
  nohup python3 "$APEXCORE_DIR/cmd-api/server.py" \
  >> /var/log/cmd-api.log 2>&1 &
sleep 2

if curl -sf http://localhost:7070/health &>/dev/null; then
  ok "cmd-api: running on :7070"
else
  warn "cmd-api: not responding — check /var/log/cmd-api.log"
fi

# ── 10. Dispatcher ────────────────────────────────────────────────────────────
log "Starting dispatcher..."
pkill -f "hermes_dispatcher.py" 2>/dev/null || true
sleep 1
ENV_FILE="$APEXCORE_DIR/cmd-api/.env.dispatcher"
if [ -f "$ENV_FILE" ] && [ -f "$APEXCORE_DIR/cmd-api/hermes_dispatcher.py" ]; then
  set -a; source "$ENV_FILE"; set +a
  nohup python3 "$APEXCORE_DIR/cmd-api/hermes_dispatcher.py" \
    >> /var/log/apexcore-dispatcher.log 2>&1 &
  sleep 2
  if curl -sf http://localhost:7071/health &>/dev/null; then
    ok "dispatcher: running on :7071"
  else
    warn "dispatcher: not responding — check /var/log/apexcore-dispatcher.log"
  fi
else
  warn "dispatcher: hermes_dispatcher.py or .env.dispatcher not found — skipping"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  Bootstrap complete — $(date '+%H:%M:%S')"
echo "  Run smoke test: $APEXCORE_DIR/scripts/smoke-test.sh"
echo "═══════════════════════════════════════════════════"
echo ""
