#!/usr/bin/env bash
# ApexCore VPS bootstrap — installs cmd-api with /deploy endpoint + systemd auto-restart
# Usage: bash <(curl -fsSL "https://raw.githubusercontent.com/AIA2025/apexcore/claude/serene-gates-KHDWp/scripts/bootstrap.sh")
set -euo pipefail

BRANCH="${1:-claude/serene-gates-KHDWp}"
BASE="https://raw.githubusercontent.com/AIA2025/apexcore/${BRANCH}"
SRV="/opt/apexcore/cmd-api/server.py"
LOG="/var/log/cmd-api.log"
SERVICE="/etc/systemd/system/cmd-api.service"

echo "╔══════════════════════════════════════════════╗"
echo "║  ApexCore CMD-API Bootstrap                  ║"
echo "║  Branch: ${BRANCH}"
echo "╚══════════════════════════════════════════════╝"
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
StandardOutput=append:/var/log/cmd-api.log
StandardError=append:/var/log/cmd-api.log
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
  echo "  Deploy log: tail -f /var/log/cmd-api-deploy.log"
  echo "══════════════════════════════════════════════"
else
  echo "WARNING: /deploy returned unexpected response"
  echo "Check: journalctl -u cmd-api -n 50 --no-pager"
  exit 1
fi
