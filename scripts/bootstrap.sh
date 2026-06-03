#!/usr/bin/env bash
# ApexCore VPS bootstrap — installs cmd-api with /deploy endpoint + systemd auto-restart
# Usage: bash <(curl -fsSL "https://raw.githubusercontent.com/AIA2025/apexcore/claude/serene-gates-KHDWp/scripts/bootstrap.sh")
set -euo pipefail

BRANCH="${1:-${APEXCORE_BRANCH:-main}}"
BASE="https://raw.githubusercontent.com/AIA2025/apexcore/${BRANCH}"
SRV="/opt/apexcore/cmd-api/server.py"
LOG="/tmp/cmd-api.log"
SERVICE="/etc/systemd/system/cmd-api.service"
APEXCORE_DIR="/srv/apexcore"

echo "╔══════════════════════════════════════════════╗"
echo "║  ApexCore CMD-API Bootstrap                  ║"
echo "║  Branch: ${BRANCH}"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 0. Git pull + nginx vhost ─────────────────────────
if [ -d "$APEXCORE_DIR/.git" ]; then
  echo "[0/5] Pulling latest code..."
  git -C "$APEXCORE_DIR" stash push -m "bootstrap-$(date +%s)" 2>/dev/null || true
  git -C "$APEXCORE_DIR" fetch origin 2>/dev/null
  git -C "$APEXCORE_DIR" checkout "$BRANCH" 2>/dev/null || true
  git -C "$APEXCORE_DIR" pull origin "$BRANCH" 2>/dev/null && echo "      ✓ git pull" || echo "      ⚠ git pull failed (continuing)"
  # Apply nginx vhost from repo
  VHOST_SRC="$APEXCORE_DIR/infra-compose/nginx-vhost.conf"
  if [ -f "$VHOST_SRC" ] && command -v nginx &>/dev/null; then
    cp "$VHOST_SRC" /etc/nginx/sites-available/apexcore.conf
    mkdir -p /etc/nginx/sites-enabled
    [ -L /etc/nginx/sites-enabled/apexcore.conf ] || ln -sf /etc/nginx/sites-available/apexcore.conf /etc/nginx/sites-enabled/apexcore.conf
    nginx -t 2>/dev/null && nginx -s reload && echo "      ✓ nginx vhost updated" || echo "      ⚠ nginx reload failed"
  fi
else
  echo "[0/5] Skipping git pull (repo not found at $APEXCORE_DIR)"
fi
echo ""

# ── 1. Download ──────────────────────────────────────
echo "[1/5] Downloading cmd-api/server.py from GitHub..."
curl -fsSL "${BASE}/cmd-api/server.py" -o /tmp/cmd-api-server.py
grep -q 'run_deploy' /tmp/cmd-api-server.py \
  || { echo "ERROR: downloaded file has no run_deploy — branch not pushed yet?"; exit 1; }
mkdir -p /opt/apexcore/cmd-api /srv/apexcore/cmd-api
cp /tmp/cmd-api-server.py "$SRV"
cp /tmp/cmd-api-server.py /srv/apexcore/cmd-api/server.py
echo "      ✓"

# ── 2. Systemd service ───────────────────────────────
echo "[2/5] Installing systemd service..."
cat > "$SERVICE" <<'UNIT'
[Unit]
Description=ApexCore CMD API
After=network.target

[Service]
ExecStartPre=/bin/bash -c 'fuser -k 7070/tcp 2>/dev/null || true; sleep 1'
ExecStart=/usr/bin/python3 /opt/apexcore/cmd-api/server.py
Restart=always
RestartSec=5
StartLimitAction=none
StandardOutput=append:/tmp/cmd-api.log
StandardError=append:/tmp/cmd-api.log
WorkingDirectory=/opt/apexcore/cmd-api
Environment=CMD_TOKEN=

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable cmd-api --quiet
echo "      ✓"

# ── 3. (Re)start ─────────────────────────────────────
echo "[3/5] Stopping any running cmd-api processes..."
systemctl stop cmd-api 2>/dev/null || true
fuser -k 7070/tcp 2>/dev/null || true
pkill -f "cmd-api/server.py" 2>/dev/null || true
sleep 2
echo "      Starting service..."
systemctl start cmd-api
sleep 3
echo "      ✓"

# ── 3b. Open firewall ports ───────────────────────────
ufw allow 7070/tcp 2>/dev/null && echo "      ufw: 7070/tcp allowed" || true
ufw allow 8000/tcp 2>/dev/null && echo "      ufw: 8000/tcp allowed" || true

# ── 4. Health check ──────────────────────────────────
echo "[4/5] Health check (port 7070)..."
HEALTH=$(curl -sf http://localhost:7070/health || echo "FAILED")
echo "      ${HEALTH}"
echo "$HEALTH" | grep -q '"ok"' || { echo "ERROR: health check failed"; journalctl -u cmd-api -n 20 --no-pager; exit 1; }

# ── 5. /deploy smoke test ────────────────────────────
echo "[5/5] Testing /deploy endpoint..."
RESP=$(curl -s -X POST http://localhost:7070/deploy \
  -H "Content-Type: application/json" \
  -d "{\"branch\":\"${BRANCH}\"}")
echo "      ${RESP}"

echo ""
if echo "$RESP" | grep -q '"deploying"'; then
  echo "══════════════════════════════════════════════"
  echo "  Bootstrap complete."
  echo "  cmd-api is running, /deploy works, self-update active."
  echo "  systemd will auto-restart it on reboot."
  echo ""
  echo "  Live logs:  journalctl -u cmd-api -f"
  echo "  Deploy log: tail -f /tmp/cmd-api-deploy.log"
  echo "══════════════════════════════════════════════"
elif echo "$RESP" | grep -q '"unauthorized"'; then
  echo "══════════════════════════════════════════════"
  echo "  Bootstrap complete."
  echo "  cmd-api is running, token auth is enforced (CMD_TOKEN set)."
  echo "  CI will authenticate via CMD_API_TOKEN secret."
  echo ""
  echo "  Live logs:  journalctl -u cmd-api -f"
  echo "  Deploy log: tail -f /tmp/cmd-api-deploy.log"
  echo "══════════════════════════════════════════════"
else
  echo "ERROR: /deploy returned unexpected response"
  echo "Check: journalctl -u cmd-api -n 50 --no-pager"
  exit 1
fi
