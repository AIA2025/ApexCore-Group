#!/bin/bash
# ApexCore Complete Setup — alles in einem Lauf
# Läuft auch wenn vorherige Schritte teilweise fehlschlugen

N8N="http://localhost:5679"
EMAIL="m.dordevic@apexcore.group"
PASS="Trustno1981!"
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
  git fetch origin claude/n8n-owner-setup-Y5cCp 2>&1 | tail -1
  git checkout claude/n8n-owner-setup-Y5cCp 2>&1 | tail -1
  git pull origin claude/n8n-owner-setup-Y5cCp 2>&1 | tail -1
  ok "Repo aktuell"
else
  git clone https://github.com/AIA2025/apexcore /opt/apexcore 2>&1 | tail -2
  cd /opt/apexcore
  git checkout claude/n8n-owner-setup-Y5cCp 2>&1 | tail -1
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
LOGIN=$(curl -s -c "$COOKIE" -X POST "$N8N/rest/login" \
  -H "Content-Type: application/json" \
  -d "{\"emailOrLdapLoginId\":\"$EMAIL\",\"password\":\"$PASS\"}" 2>/dev/null)

if echo "$LOGIN" | grep -q '"id"'; then
  FNAME=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('firstName','?'))" 2>/dev/null)
  ok "Login OK — $FNAME"
else
  err "Login fehlgeschlagen: $(echo $LOGIN | head -c 100)"
  rm -f "$COOKIE"
  exit 1
fi

# ─── 4. CREDENTIALS ───────────────────────────
echo ""
echo "[ 4/6 ] Credentials..."
CREDS=$(curl -s -b "$COOKIE" "$N8N/rest/credentials" 2>/dev/null)

ANTHROPIC_ID=$(echo "$CREDS" | python3 -c "
import sys,json
try:
  data=json.load(sys.stdin)
  items=data.get('data',data) if isinstance(data,dict) else data
  for c in (items if isinstance(items,list) else []):
    if c.get('type')=='anthropicApi': print(c['id']); break
except: pass
" 2>/dev/null)

NOTION_ID=$(echo "$CREDS" | python3 -c "
import sys,json
try:
  data=json.load(sys.stdin)
  items=data.get('data',data) if isinstance(data,dict) else data
  for c in (items if isinstance(items,list) else []):
    if c.get('type')=='notionApi': print(c['id']); break
except: pass
" 2>/dev/null)

[ -n "$ANTHROPIC_ID" ] && ok "Anthropic Credential gefunden (ID: $ANTHROPIC_ID)" || err "Anthropic Credential FEHLT"
[ -n "$NOTION_ID" ]    && ok "Notion Credential gefunden (ID: $NOTION_ID)"    || err "Notion Credential FEHLT"

# Credentials wurden bereits per Kodee angelegt — IDs sind Pflicht
if [ -z "$ANTHROPIC_ID" ]; then
  err "Anthropic Credential nicht gefunden — bitte in n8n UI unter Credentials prüfen"
fi
if [ -z "$NOTION_ID" ]; then
  err "Notion Credential nicht gefunden — bitte in n8n UI unter Credentials prüfen"
fi

# ─── 5. WORKFLOWS ─────────────────────────────
echo ""
echo "[ 5/6 ] Workflows..."

EXISTING=$(curl -s -b "$COOKIE" "$N8N/rest/workflows" 2>/dev/null | python3 -c "
import sys,json
try:
  data=json.load(sys.stdin)
  items=data.get('data',data) if isinstance(data,dict) else data
  for w in (items if isinstance(items,list) else []): print(w.get('name',''))
except: pass
" 2>/dev/null)

create_workflow_file() {
  local NAME="$1"
  local FILE="$2"
  if echo "$EXISTING" | grep -qF "$NAME"; then
    inf "Workflow '$NAME' bereits vorhanden — überspringe"
    return
  fi
  if [ ! -f "$FILE" ]; then
    err "Workflow-Datei nicht gefunden: $FILE"
    return
  fi
  # Credential IDs + Port in JSON einsetzen
  local JSON
  JSON=$(sed \
    -e "s/__ANTHROPIC_ID__/$ANTHROPIC_ID/g" \
    -e "s/__NOTION_ID__/$NOTION_ID/g" \
    -e "s/__NOTION_DB_ID__/NOTION_DB_ID_EINTRAGEN/g" \
    "$FILE")
  RESP=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
    -H "Content-Type: application/json" \
    --data-binary "$JSON" 2>/dev/null)
  WF_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null)
  if [ -n "$WF_ID" ] && [ "$WF_ID" != "None" ] && [ "$WF_ID" != "" ]; then
    ok "Workflow '$NAME' erstellt (ID: $WF_ID)"
    curl -s -b "$COOKIE" -X PATCH "$N8N/rest/workflows/$WF_ID" \
      -H "Content-Type: application/json" \
      -d '{"active":true}' > /dev/null 2>&1
  else
    err "Workflow '$NAME' fehlgeschlagen: $(echo $RESP | head -c 150)"
  fi
}

WF_DIR="$SCRIPT_DIR/n8n-workflows"
create_workflow_file "Claude Webhook"    "$WF_DIR/01-claude-webhook.json"
create_workflow_file "Notion Logger"     "$WF_DIR/02-notion-logger.json"
create_workflow_file "Heartbeat Monitor" "$WF_DIR/03-heartbeat-monitor.json"

# ─── 6. DASHBOARD DEPLOYEN ────────────────────
echo ""
echo "[ 6/6 ] Dashboard..."

mkdir -p /opt/apexcore-dashboard
cp /opt/apexcore/dashboard/index.html /opt/apexcore-dashboard/index.html

# Prüfe ob Container schon läuft
if docker ps --format '{{.Names}}' | grep -q "apexcore-operator-ui"; then
  ok "Dashboard Container läuft bereits"
else
  docker run -d \
    --name apexcore-operator-ui \
    --restart unless-stopped \
    -p 9090:80 \
    -v /opt/apexcore-dashboard:/usr/share/nginx/html:ro \
    nginx:alpine > /dev/null 2>&1 \
    && ok "Dashboard gestartet auf Port 9090" \
    || err "Dashboard Start fehlgeschlagen"
fi

# Port 9090 in UFW freigeben falls aktiv
if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
  ufw allow 9090/tcp > /dev/null 2>&1 && inf "Port 9090 in UFW freigegeben"
fi

# ─── FINAL STATUS REPORT ─────────────────────
echo ""
echo "========================================"
echo "  FINAL STATUS"
echo "========================================"
echo ""

# Workflows auflisten
echo "📋 n8n Workflows:"
curl -s -b "$COOKIE" "$N8N/rest/workflows" 2>/dev/null | python3 -c "
import sys,json
try:
  data=json.load(sys.stdin)
  items=data.get('data',data) if isinstance(data,dict) else data
  for w in (items if isinstance(items,list) else []):
    active='✅ AKTIV' if w.get('active') else '⏸  INAKTIV'
    print(f'  {active}  {w.get(\"name\",\"?\")}  (ID: {w.get(\"id\",\"?\")})')
except Exception as e: print('  Fehler:', e)
" 2>/dev/null

echo ""
echo "🐳 Docker Services:"
docker ps --format '  {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -v "^$"

echo ""
echo "🌐 Dashboard:"
DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:9090 2>/dev/null)
[ "$DASH_STATUS" = "200" ] \
  && echo "  ✅ http://76.13.138.73:9090 — erreichbar" \
  || echo "  ❌ Dashboard nicht erreichbar (HTTP $DASH_STATUS)"

echo ""
echo "⚡ Webhook URLs (sofort nutzbar):"
echo "  POST http://76.13.138.73:5679/webhook/claude"
echo "       Body: {\"message\": \"Hallo Claude\"}"
echo ""
echo "  POST http://76.13.138.73:5679/webhook/log"
echo "       Body: {\"title\": \"Test\", \"content\": \"Inhalt\"}"
echo ""
echo "⚠️  TODO: Notion Database ID in n8n eintragen"
echo "  → Workflows 'Notion Logger' und 'Heartbeat Monitor'"
echo ""
echo "========================================"
echo "  Setup abgeschlossen: $(date)"
echo "========================================"

rm -f "$COOKIE"
