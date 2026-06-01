#!/bin/bash
# ApexCore n8n Deployment Script
# Erstellt alle Workflows und deployt das Dashboard

set -e

N8N="http://localhost:5678"
EMAIL="m.dordevic@apexcore.group"
PASS="Trustno1981!"
COOKIE="/tmp/apexcore_n8n.txt"

echo "╔══════════════════════════════════════╗"
echo "║     ApexCore n8n Setup v1.0          ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ─── Login ───────────────────────────────────
echo "▶ Login..."
LOGIN=$(curl -s -c "$COOKIE" -X POST "$N8N/rest/login" \
  -H "Content-Type: application/json" \
  -d "{\"emailOrLdapLoginId\":\"$EMAIL\",\"password\":\"$PASS\"}")

if echo "$LOGIN" | grep -q '"firstName"'; then
  NAME=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('firstName','?'))" 2>/dev/null)
  echo "  ✅ Login OK — Hallo $NAME"
else
  echo "  ❌ Login fehlgeschlagen: $LOGIN"
  exit 1
fi

# ─── Credential IDs holen ────────────────────
echo ""
echo "▶ Lade Credentials..."
CREDS=$(curl -s -b "$COOKIE" "$N8N/rest/credentials")

ANTHROPIC_ID=$(echo "$CREDS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', data) if isinstance(data, dict) else data
for c in (items if isinstance(items, list) else []):
    if c.get('type') == 'anthropicApi':
        print(c['id']); break
" 2>/dev/null)

NOTION_ID=$(echo "$CREDS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', data) if isinstance(data, dict) else data
for c in (items if isinstance(items, list) else []):
    if c.get('type') == 'notionApi':
        print(c['id']); break
" 2>/dev/null)

echo "  Anthropic ID: ${ANTHROPIC_ID:-NICHT GEFUNDEN}"
echo "  Notion ID:    ${NOTION_ID:-NICHT GEFUNDEN}"

if [ -z "$ANTHROPIC_ID" ] || [ -z "$NOTION_ID" ]; then
  echo "  ⚠️  Credentials nicht gefunden — bitte in n8n UI anlegen"
fi

# ─── Workflow 1: Claude Webhook ───────────────
echo ""
echo "▶ Erstelle Workflow 1: Claude Webhook..."

WF1=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"Claude Webhook\",
  \"active\": true,
  \"settings\": {\"executionOrder\": \"v1\"},
  \"nodes\": [
    {
      \"parameters\": {\"httpMethod\": \"POST\", \"path\": \"claude\", \"responseMode\": \"responseNode\", \"options\": {}},
      \"id\": \"wh-claude-01\",
      \"name\": \"Webhook\",
      \"type\": \"n8n-nodes-base.webhook\",
      \"typeVersion\": 2,
      \"position\": [250, 300],
      \"webhookId\": \"apexcore-claude\"
    },
    {
      \"parameters\": {
        \"method\": \"POST\",
        \"url\": \"https://api.anthropic.com/v1/messages\",
        \"sendHeaders\": true,
        \"headerParameters\": {\"parameters\": [
          {\"name\": \"anthropic-version\", \"value\": \"2023-06-01\"},
          {\"name\": \"x-api-key\", \"value\": \"={{ \$credentials.anthropicApi.apiKey }}\"}
        ]},
        \"sendBody\": true,
        \"contentType\": \"json\",
        \"bodyParameters\": {\"parameters\": [
          {\"name\": \"model\", \"value\": \"claude-opus-4-5-20251101\"},
          {\"name\": \"max_tokens\", \"value\": 2048},
          {\"name\": \"messages\", \"value\": \"=[{\\\"role\\\": \\\"user\\\", \\\"content\\\": \\\"{{ \$json.body.message }}\\\"}]\"}
        ]},
        \"options\": {}
      },
      \"id\": \"http-claude-01\",
      \"name\": \"Claude API\",
      \"type\": \"n8n-nodes-base.httpRequest\",
      \"typeVersion\": 4.2,
      \"position\": [500, 300],
      \"credentials\": {\"anthropicApi\": {\"id\": \"${ANTHROPIC_ID}\", \"name\": \"Anthropic (Claude)\"}}
    },
    {
      \"parameters\": {
        \"respondWith\": \"json\",
        \"responseBody\": \"={ \\\"response\\\": \\\"{{ \$json.content[0].text }}\\\", \\\"model\\\": \\\"{{ \$json.model }}\\\" }\",
        \"options\": {}
      },
      \"id\": \"resp-claude-01\",
      \"name\": \"Respond\",
      \"type\": \"n8n-nodes-base.respondToWebhook\",
      \"typeVersion\": 1.1,
      \"position\": [750, 300]
    }
  ],
  \"connections\": {
    \"Webhook\": {\"main\": [[{\"node\": \"Claude API\", \"type\": \"main\", \"index\": 0}]]},
    \"Claude API\": {\"main\": [[{\"node\": \"Respond\", \"type\": \"main\", \"index\": 0}]]}
  }
}")

WF1_ID=$(echo "$WF1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id','ERROR'))" 2>/dev/null)
echo "  ✅ Workflow 1 ID: $WF1_ID"

# ─── Workflow 2: Notion Logger ────────────────
echo ""
echo "▶ Erstelle Workflow 2: Notion Logger..."

WF2=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"Notion Logger\",
  \"active\": true,
  \"settings\": {\"executionOrder\": \"v1\"},
  \"nodes\": [
    {
      \"parameters\": {\"httpMethod\": \"POST\", \"path\": \"log\", \"responseMode\": \"responseNode\", \"options\": {}},
      \"id\": \"wh-notion-01\",
      \"name\": \"Webhook\",
      \"type\": \"n8n-nodes-base.webhook\",
      \"typeVersion\": 2,
      \"position\": [250, 300],
      \"webhookId\": \"apexcore-log\"
    },
    {
      \"parameters\": {
        \"resource\": \"databasePage\",
        \"operation\": \"create\",
        \"databaseId\": {\"__rl\": true, \"value\": \"DEINE_NOTION_DB_ID\", \"mode\": \"id\"},
        \"title\": \"={{ \$json.body.title || 'Log ' + new Date().toISOString() }}\",
        \"propertiesUi\": {\"propertyValues\": []},
        \"blockUi\": {\"blockValues\": [{\"type\": \"paragraph\", \"paragraph\": \"={{ \$json.body.content || '' }}\"}]},
        \"options\": {}
      },
      \"id\": \"notion-log-01\",
      \"name\": \"Notion Create\",
      \"type\": \"n8n-nodes-base.notion\",
      \"typeVersion\": 2.2,
      \"position\": [500, 300],
      \"credentials\": {\"notionApi\": {\"id\": \"${NOTION_ID}\", \"name\": \"Notion API\"}}
    },
    {
      \"parameters\": {
        \"respondWith\": \"json\",
        \"responseBody\": \"={ \\\"status\\\": \\\"logged\\\", \\\"page_id\\\": \\\"{{ \$json.id }}\\\" }\",
        \"options\": {}
      },
      \"id\": \"resp-notion-01\",
      \"name\": \"Respond\",
      \"type\": \"n8n-nodes-base.respondToWebhook\",
      \"typeVersion\": 1.1,
      \"position\": [750, 300]
    }
  ],
  \"connections\": {
    \"Webhook\": {\"main\": [[{\"node\": \"Notion Create\", \"type\": \"main\", \"index\": 0}]]},
    \"Notion Create\": {\"main\": [[{\"node\": \"Respond\", \"type\": \"main\", \"index\": 0}]]}
  }
}")

WF2_ID=$(echo "$WF2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id','ERROR'))" 2>/dev/null)
echo "  ✅ Workflow 2 ID: $WF2_ID"

# ─── Workflow 3: Heartbeat Monitor ───────────
echo ""
echo "▶ Erstelle Workflow 3: Heartbeat Monitor..."

WF3=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"Heartbeat Monitor\",
  \"active\": true,
  \"settings\": {\"executionOrder\": \"v1\"},
  \"nodes\": [
    {
      \"parameters\": {\"rule\": {\"interval\": [{\"field\": \"hours\", \"hoursInterval\": 12}]}},
      \"id\": \"sched-hb-01\",
      \"name\": \"Every 12h\",
      \"type\": \"n8n-nodes-base.scheduleTrigger\",
      \"typeVersion\": 1.1,
      \"position\": [250, 300]
    },
    {
      \"parameters\": {
        \"jsCode\": \"const services = [\\n  { name: 'n8n', url: 'http://localhost:5679' },\\n  { name: 'Hermes', url: 'http://localhost:8787' },\\n  { name: 'Ollama', url: 'http://localhost:3000' },\\n  { name: 'Paperclip', url: 'http://localhost:52309' },\\n  { name: 'Dashboard', url: 'http://localhost:3011' }\\n];\\nconst results = [];\\nfor (const s of services) {\\n  try {\\n    await this.helpers.httpRequest({ method: 'GET', url: s.url, timeout: 5000 });\\n    results.push({ name: s.name, status: 'online' });\\n  } catch(e) {\\n    results.push({ name: s.name, status: 'offline', error: e.message.substring(0,80) });\\n  }\\n}\\nconst online = results.filter(r => r.status === 'online').length;\\nconst summary = results.map(r => r.status === 'online' ? '✅ ' + r.name : '❌ ' + r.name).join(', ');\\nreturn [{ json: { services: results, online, total: results.length, summary, timestamp: new Date().toISOString() } }];\"
      },
      \"id\": \"code-hb-01\",
      \"name\": \"Check Services\",
      \"type\": \"n8n-nodes-base.code\",
      \"typeVersion\": 2,
      \"position\": [500, 300]
    },
    {
      \"parameters\": {
        \"resource\": \"databasePage\",
        \"operation\": \"create\",
        \"databaseId\": {\"__rl\": true, \"value\": \"DEINE_NOTION_DB_ID\", \"mode\": \"id\"},
        \"title\": \"={{ 'Heartbeat ' + \$json.timestamp.substring(0,10) + ' — ' + \$json.online + '/' + \$json.total + ' online' }}\",
        \"propertiesUi\": {\"propertyValues\": []},
        \"blockUi\": {\"blockValues\": [{\"type\": \"paragraph\", \"paragraph\": \"={{ \$json.summary }}\"}]},
        \"options\": {}
      },
      \"id\": \"notion-hb-01\",
      \"name\": \"Log to Notion\",
      \"type\": \"n8n-nodes-base.notion\",
      \"typeVersion\": 2.2,
      \"position\": [750, 300],
      \"credentials\": {\"notionApi\": {\"id\": \"${NOTION_ID}\", \"name\": \"Notion API\"}}
    }
  ],
  \"connections\": {
    \"Every 12h\": {\"main\": [[{\"node\": \"Check Services\", \"type\": \"main\", \"index\": 0}]]},
    \"Check Services\": {\"main\": [[{\"node\": \"Log to Notion\", \"type\": \"main\", \"index\": 0}]]}
  }
}")

WF3_ID=$(echo "$WF3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id','ERROR'))" 2>/dev/null)
echo "  ✅ Workflow 3 ID: $WF3_ID"

# ─── Dashboard deployen ───────────────────────
echo ""
echo "▶ Deploye Dashboard..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_SRC="$SCRIPT_DIR/dashboard/index.html"

if [ -f "$DASHBOARD_SRC" ]; then
  mkdir -p /opt/apexcore-dashboard
  cp "$DASHBOARD_SRC" /opt/apexcore-dashboard/index.html

  # Prüfe ob nginx/apache läuft
  if docker ps --format '{{.Names}}' | grep -q 'nginx\|apache'; then
    echo "  ✅ Dashboard-Datei bereitgestellt"
  else
    # Starte minimalen nginx Container
    docker run -d \
      --name apexcore-operator-ui \
      --restart unless-stopped \
      -p 9090:80 \
      -v /opt/apexcore-dashboard:/usr/share/nginx/html:ro \
      nginx:alpine 2>/dev/null && echo "  ✅ Dashboard läuft auf http://76.13.138.73:9090" \
      || echo "  ℹ️  Dashboard-Datei unter /opt/apexcore-dashboard/index.html"
  fi
else
  echo "  ⚠️  dashboard/index.html nicht gefunden — erst 'git pull' ausführen"
fi

# ─── Summary ─────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║           Setup Abgeschlossen!       ║"
echo "╠══════════════════════════════════════╣"
echo "║ Workflow 1 (Claude Webhook):         ║"
echo "║   POST /webhook/claude               ║"
echo "║   Body: {\"message\": \"Deine Frage\"}   ║"
echo "║                                      ║"
echo "║ Workflow 2 (Notion Logger):          ║"
echo "║   POST /webhook/log                  ║"
echo "║   Body: {\"title\": \"\", \"content\": \"\"} ║"
echo "║                                      ║"
echo "║ Workflow 3 (Heartbeat):              ║"
echo "║   Automatisch alle 12h               ║"
echo "║                                      ║"
echo "║ ⚠️  Notion DB ID noch setzen in:     ║"
echo "║   n8n → Workflows 2 & 3              ║"
echo "╚══════════════════════════════════════╝"

rm -f "$COOKIE"
