#!/bin/bash
# ApexCore Complete Setup — alles in einem Lauf
# Läuft auch wenn vorherige Schritte teilweise fehlschlugen

N8N="http://localhost:5679"
EMAIL="m.dordevic@apexcore.group"
PASS="Trustno1981!"
COOKIE="/tmp/ac_session.txt"
LOG="/tmp/apexcore_setup.log"
REPORT=""

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

# Bestehende Workflows abrufen
EXISTING=$(curl -s -b "$COOKIE" "$N8N/rest/workflows" 2>/dev/null | python3 -c "
import sys,json
try:
  data=json.load(sys.stdin)
  items=data.get('data',data) if isinstance(data,dict) else data
  for w in (items if isinstance(items,list) else []):
    print(w.get('name',''))
except: pass
" 2>/dev/null)

create_workflow() {
  local NAME="$1"
  local JSON="$2"
  if echo "$EXISTING" | grep -qF "$NAME"; then
    inf "Workflow '$NAME' bereits vorhanden — überspringe"
    return
  fi
  RESP=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
    -H "Content-Type: application/json" \
    -d "$JSON" 2>/dev/null)
  WF_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id',''))" 2>/dev/null)
  if [ -n "$WF_ID" ] && [ "$WF_ID" != "None" ]; then
    ok "Workflow '$NAME' erstellt (ID: $WF_ID)"
    # Aktivieren
    curl -s -b "$COOKIE" -X PATCH "$N8N/rest/workflows/$WF_ID" \
      -H "Content-Type: application/json" \
      -d '{"active":true}' > /dev/null 2>&1
  else
    err "Workflow '$NAME' fehlgeschlagen: $(echo $RESP | head -c 120)"
  fi
}

# Workflow 1: Claude Webhook
create_workflow "Claude Webhook" "{
  \"name\":\"Claude Webhook\",
  \"active\":true,
  \"settings\":{\"executionOrder\":\"v1\"},
  \"nodes\":[
    {\"parameters\":{\"httpMethod\":\"POST\",\"path\":\"claude\",\"responseMode\":\"responseNode\",\"options\":{}},
     \"id\":\"wh01\",\"name\":\"Webhook\",\"type\":\"n8n-nodes-base.webhook\",\"typeVersion\":2,\"position\":[250,300]},
    {\"parameters\":{
       \"method\":\"POST\",\"url\":\"https://api.anthropic.com/v1/messages\",
       \"sendHeaders\":true,
       \"headerParameters\":{\"parameters\":[
         {\"name\":\"anthropic-version\",\"value\":\"2023-06-01\"},
         {\"name\":\"x-api-key\",\"value\":\"={{ \\\$credentials.anthropicApi.apiKey }}\"}
       ]},
       \"sendBody\":true,\"contentType\":\"json\",
       \"specifyBody\":\"json\",
       \"jsonBody\":\"={ \\\\\\\"model\\\\\\\": \\\\\\\"claude-opus-4-5-20251101\\\\\\\", \\\\\\\"max_tokens\\\\\\\": 2048, \\\\\\\"messages\\\\\\\": [{ \\\\\\\"role\\\\\\\": \\\\\\\"user\\\\\\\", \\\\\\\"content\\\\\\\": \\\\\\\"{{ \\\$json.body.message }}\\\\\\\" }] }\",
       \"options\":{}},
     \"id\":\"http01\",\"name\":\"Claude API\",\"type\":\"n8n-nodes-base.httpRequest\",\"typeVersion\":4.2,\"position\":[500,300],
     \"credentials\":{\"anthropicApi\":{\"id\":\"$ANTHROPIC_ID\",\"name\":\"Anthropic (Claude)\"}}},
    {\"parameters\":{\"respondWith\":\"json\",\"responseBody\":\"={ \\\\\\\"response\\\\\\\": \\\\\\\"{{ \\\$json.content[0].text }}\\\\\\\" }\",\"options\":{}},
     \"id\":\"resp01\",\"name\":\"Respond\",\"type\":\"n8n-nodes-base.respondToWebhook\",\"typeVersion\":1.1,\"position\":[750,300]}
  ],
  \"connections\":{
    \"Webhook\":{\"main\":[[{\"node\":\"Claude API\",\"type\":\"main\",\"index\":0}]]},
    \"Claude API\":{\"main\":[[{\"node\":\"Respond\",\"type\":\"main\",\"index\":0}]]}
  }
}"

# Workflow 2: Notion Logger
create_workflow "Notion Logger" "{
  \"name\":\"Notion Logger\",
  \"active\":true,
  \"settings\":{\"executionOrder\":\"v1\"},
  \"nodes\":[
    {\"parameters\":{\"httpMethod\":\"POST\",\"path\":\"log\",\"responseMode\":\"responseNode\",\"options\":{}},
     \"id\":\"wh02\",\"name\":\"Webhook\",\"type\":\"n8n-nodes-base.webhook\",\"typeVersion\":2,\"position\":[250,300]},
    {\"parameters\":{
       \"resource\":\"databasePage\",\"operation\":\"create\",
       \"databaseId\":{\"__rl\":true,\"value\":\"NOTION_DB_ID_HIER_EINTRAGEN\",\"mode\":\"id\"},
       \"title\":\"={{ \\\$json.body.title || 'Log ' + new Date().toISOString() }}\",
       \"propertiesUi\":{\"propertyValues\":[]},
       \"blockUi\":{\"blockValues\":[{\"type\":\"paragraph\",\"paragraph\":\"={{ \\\$json.body.content || '' }}\"}]},
       \"options\":{}},
     \"id\":\"notion02\",\"name\":\"Notion\",\"type\":\"n8n-nodes-base.notion\",\"typeVersion\":2.2,\"position\":[500,300],
     \"credentials\":{\"notionApi\":{\"id\":\"$NOTION_ID\",\"name\":\"Notion API\"}}},
    {\"parameters\":{\"respondWith\":\"json\",\"responseBody\":\"={ \\\\\\\"status\\\\\\\": \\\\\\\"logged\\\\\\\" }\",\"options\":{}},
     \"id\":\"resp02\",\"name\":\"Respond\",\"type\":\"n8n-nodes-base.respondToWebhook\",\"typeVersion\":1.1,\"position\":[750,300]}
  ],
  \"connections\":{
    \"Webhook\":{\"main\":[[{\"node\":\"Notion\",\"type\":\"main\",\"index\":0}]]},
    \"Notion\":{\"main\":[[{\"node\":\"Respond\",\"type\":\"main\",\"index\":0}]]}
  }
}"

# Workflow 3: Heartbeat Monitor
create_workflow "Heartbeat Monitor" "{
  \"name\":\"Heartbeat Monitor\",
  \"active\":true,
  \"settings\":{\"executionOrder\":\"v1\"},
  \"nodes\":[
    {\"parameters\":{\"rule\":{\"interval\":[{\"field\":\"hours\",\"hoursInterval\":12}]}},
     \"id\":\"sched03\",\"name\":\"Every 12h\",\"type\":\"n8n-nodes-base.scheduleTrigger\",\"typeVersion\":1.1,\"position\":[250,300]},
    {\"parameters\":{\"jsCode\":\"const svcs=[{name:'n8n',url:'http://localhost:5679'},{name:'Hermes',url:'http://localhost:8787'},{name:'Ollama',url:'http://localhost:3000'},{name:'Paperclip',url:'http://localhost:52309'},{name:'Dashboard',url:'http://localhost:3011'}];const r=[];for(const s of svcs){try{await this.helpers.httpRequest({method:'GET',url:s.url,timeout:5000});r.push({name:s.name,status:'online'});}catch(e){r.push({name:s.name,status:'offline'});}}const online=r.filter(x=>x.status==='online').length;const summary=r.map(x=>(x.status==='online'?'✅ ':'❌ ')+x.name).join(' | ');return [{json:{services:r,online,total:r.length,summary,ts:new Date().toISOString()}}];\"},
     \"id\":\"code03\",\"name\":\"Check All\",\"type\":\"n8n-nodes-base.code\",\"typeVersion\":2,\"position\":[500,300]},
    {\"parameters\":{
       \"resource\":\"databasePage\",\"operation\":\"create\",
       \"databaseId\":{\"__rl\":true,\"value\":\"NOTION_DB_ID_HIER_EINTRAGEN\",\"mode\":\"id\"},
       \"title\":\"={{ 'Heartbeat ' + \\\$json.ts.substring(0,10) + ' — ' + \\\$json.online + '/' + \\\$json.total }}\",
       \"propertiesUi\":{\"propertyValues\":[]},
       \"blockUi\":{\"blockValues\":[{\"type\":\"paragraph\",\"paragraph\":\"={{ \\\$json.summary }}\"}]},
       \"options\":{}},
     \"id\":\"notion03\",\"name\":\"Log Notion\",\"type\":\"n8n-nodes-base.notion\",\"typeVersion\":2.2,\"position\":[750,300],
     \"credentials\":{\"notionApi\":{\"id\":\"$NOTION_ID\",\"name\":\"Notion API\"}}}
  ],
  \"connections\":{
    \"Every 12h\":{\"main\":[[{\"node\":\"Check All\",\"type\":\"main\",\"index\":0}]]},
    \"Check All\":{\"main\":[[{\"node\":\"Log Notion\",\"type\":\"main\",\"index\":0}]]}
  }
}"

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
