#!/bin/bash
# ApexCore n8n Deployment Script
# Erstellt alle Workflows und deployt das Dashboard

set -e

N8N="http://localhost:5678"
EMAIL="m.dordevic@apexcore.group"
# Use environment variable N8N_PASSWORD (recommended via /root/.apexcore.env or GitHub Secrets)
PASS="${N8N_PASSWORD:-}"
COOKIE="/tmp/apexcore_n8n.txt"

if [ -z "$PASS" ]; then
  echo "ERROR: N8N_PASSWORD is not set. Export N8N_PASSWORD or add it to /root/.apexcore.env and re-run."
  exit 1
fi

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
try:
  data = json.load(sys.stdin)
  items = data.get('data', data) if isinstance(data, dict) else data
  for c in (items if isinstance(items, list) else []):
    if c.get('type') == 'anthropicApi':
        print(c['id']); break
except: pass
" 2>/dev/null)

NOTION_ID=$(echo "$CREDS" | python3 -c "
import sys, json
try:
  data = json.load(sys.stdin)
  items = data.get('data', data) if isinstance(data, dict) else data
  for c in (items if isinstance(items, list) else []):
    if c.get('type') == 'notionApi':
        print(c['id']); break
except: pass
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
  -d "{\
  \"name\": \"Claude Webhook\",\
  \"active\": true,\
  \"settings\": {\"executionOrder\": \"v1\"},\
  \"nodes\": [\
    {\
      \"parameters\": {\"httpMethod\": \"POST\", \"path\": \"claude\", \"responseMode\": \"responseNode\", \"options\": {}},\
      \"id\": \"wh-claude-01\",\
      \"name\": \"Webhook\",\
      \"type\": \"n8n-nodes-base.webhook\",\
      \"typeVersion\": 2,\
      \"position\": [250, 300],\
      \"webhookId\": \"apexcore-claude\"\
    },\
    {\
      \"parameters\": {\
        \"method\": \"POST\",\
        \"url\": \"https://api.anthropic.com/v1/messages\",\
        \"sendHeaders\": true,\
        \"headerParameters\": {\"parameters\": [\
          {\"name\": \"anthropic-version\", \"value\": \"2023-06-01\"},\
          {\"name\": \"x-api-key\", \"value\": \"={{ $credentials.anthropicApi.apiKey }}\"}\
        ]},\
        \"sendBody\": true,\
        \"contentType\": \"json\",\
        \"bodyParameters\": {\"parameters\": [\
          {\"name\": \"model\", \"value\": \"claude-opus-4-5-20251101\"},\
          {\"name\": \"max_tokens\", \"value\": 2048},\
          {\"name\": \"messages\", \"value\": \"=[{\\\"role\\\": \\\"user\\\", \\\"content\\\": $json.body.message }]\"}\
        ]},\
        \"options\": {}\
      },\
      \"id\": \"http-claude-01\",\
      \"name\": \"Claude API\",\
      \"type\": \"n8n-nodes-base.httpRequest\",\
      \"typeVersion\": 4.2,\
      \"position\": [500, 300],\
      \"credentials\": {\"anthropicApi\": {\"id\": \"${ANTHROPIC_ID}\", \"name\": \"Anthropic (Claude)\"}}\
    },\
    {\
      \"parameters\": {\"respondWith\": \"json\", \"responseBody\": \"={ \\\"response\\\": \\\"{{ $json.content[0].text }}\\\", \\\"model\\\": \\\"{{ $json.model }}\\\" }\", \"options\": {}},\
      \"id\": \"resp-claude-01\",\
      \"name\": \"Respond\",\
      \"type\": \"n8n-nodes-base.respondToWebhook\",\
      \"typeVersion\": 1.1,\
      \"position\": [750, 300]\
    }\
  ],\
  \"connections\": {\
    \"Webhook\": {\"main\": [[{\"node\": \"Claude API\", \"type\": \"main\", \"index\": 0}]]},\
    \"Claude API\": {\"main\": [[{\"node\": \"Respond\", \"type\": \"main\", \"index\": 0}]]}\
  }\
}")

WF1_ID=$(echo "$WF1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id','ERROR'))" 2>/dev/null)
echo "  ✅ Workflow 1 ID: $WF1_ID"

# ... rest of original script remains unchanged

# Clean up
rm -f "$COOKIE"
