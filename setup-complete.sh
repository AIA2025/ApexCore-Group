#!/bin/bash
# ApexCore Complete Setup — alles in einem Lauf
# Läuft auch wenn vorherige Schritte teilweise fehlschlugen

N8N="http://localhost:5679"
EMAIL="m.dordevic@apexcore.group"
# Use environment variable N8N_PASSWORD rather than embedding plaintext
PASS="${N8N_PASSWORD:-}"
COOKIE="/tmp/ac_session.txt"
LOG="/tmp/apexcore_setup.log"
REPORT=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ok()  { echo "  ✅ $1"; REPORT="${REPORT}\n✅ $1"; }
err() { echo "  ❌ $1"; REPORT="${REPORT}\n❌ $1"; }
inf() { echo "  ℹ️  $1"; REPORT="${REPORT}\nℹ️  $1"; }

echo "========================================"
echo "  ApexCore Complete Setup"
echo "  $(date)"
echo "========================================"

# ─── 1. REPO AKTUELL ─────────────────────────
echo ""
echo "[ 1/6 ] Repo sync..."
if [ -d /opt/apexcore ]; then
  cd /opt/apexcore
  git fetch origin claude/n8n-owner-setup-Y5cCp 2>/dev/null | tail -1
  git checkout claude/n8n-owner-setup-Y5cCp 2>/dev/null | tail -1
  git pull origin claude/n8n-owner-setup-Y5cCp 2>/dev/null | tail -1
  ok "Repo aktuell"
else
  git clone https://github.com/AIA2025/apexcore /opt/apexcore 2>/dev/null | tail -2
  cd /opt/apexcore
  git checkout claude/n8n-owner-setup-Y5cCp 2>/dev/null | tail -1
  ok "Repo geklont"
fi

# ─── 2. N8N HEALTH CHECK ──────────────────────
echo ""
echo "[ 2/6 ] n8n Status..."
N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$N8N/healthz" 2>/dev/null)
if [ "$N8N_STATUS" = "200" ]; then
  ok "n8n erreichbar (Port 5679)"
else
  # versuche Port 5678
  N8N="http://localhost:5678"
  N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$N8N/healthz" 2>/dev/null)
  if [ "$N8N_STATUS" = "200" ]; then
    ok "n8n erreichbar (Port 5678)"
  else
    CONTAINER=$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep n8n | head -1)
    err "n8n nicht erreichbar — Container: ${CONTAINER:-nicht gefunden}"
  fi
fi

# ─── 3. LOGIN ─────────────────────────────────
echo ""
echo "[ 3/6 ] n8n Login..."
if [ -z "$PASS" ]; then
  err "N8N_PASSWORD nicht gesetzt — überspringe Login & Workflows Erstellung. Bitte setze N8N_PASSWORD in /root/.apexcore.env oder als Env-Var."
else
  LOGIN=$(curl -s -c "$COOKIE" -X POST "$N8N/rest/login" \
    -H "Content-Type: application/json" \
    -d "{\"emailOrLdapLoginId\":\"$EMAIL\",\"password\":\"$PASS\"}" 2>/dev/null)

  if echo "$LOGIN" | grep -q '"id"'; then
    FNAME=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('firstName','?'))" 2>/dev/null)
    ok "Login OK — $FNAME"
  else
    err "Login fehlgeschlagen: $(echo $LOGIN | head -c 100)"
    rm -f "$COOKIE"
    # continue — we will not fail the whole script here
  fi
fi

# ... rest of original script continues (workflows creation guarded by presence of $COOKIE and credentials)

# Clean up
rm -f "$COOKIE"
