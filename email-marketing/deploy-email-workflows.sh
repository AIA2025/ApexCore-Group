#!/bin/bash
# ApexCore Email-Marketing n8n Workflow Deployment
# Importiert die Workflows in email-marketing/n8n-workflows/ via die n8n REST API.
# Folgt dem gleichen Login-Pattern wie deploy.sh.

set -e

N8N="${N8N_URL:-http://localhost:5678}"
EMAIL="${N8N_EMAIL:-m.dordevic@apexcore.group}"
PASS="${N8N_PASSWORD:-}"
COOKIE="/tmp/apexcore_n8n_email.txt"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$PASS" ]; then
  echo "ERROR: N8N_PASSWORD ist nicht gesetzt. Export N8N_PASSWORD oder in /root/.apexcore.env eintragen."
  exit 1
fi

echo "╔══════════════════════════════════════════╗"
echo "║  ApexCore Email-Marketing Workflows      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "▶ Login..."
LOGIN=$(curl -s -c "$COOKIE" -X POST "$N8N/rest/login" \
  -H "Content-Type: application/json" \
  -d "{\"emailOrLdapLoginId\":\"$EMAIL\",\"password\":\"$PASS\"}")

if echo "$LOGIN" | grep -q '"firstName"'; then
  echo "  ✅ Login OK"
else
  echo "  ❌ Login fehlgeschlagen: $LOGIN"
  exit 1
fi

echo ""
echo "▶ Prüfe Brevo-Credential..."
CREDS=$(curl -s -b "$COOKIE" "$N8N/rest/credentials")
BREVO_CRED_ID=$(echo "$CREDS" | python3 -c "
import sys, json
try:
  data = json.load(sys.stdin)
  items = data.get('data', data) if isinstance(data, dict) else data
  for c in (items if isinstance(items, list) else []):
    if c.get('type') == 'httpHeaderAuth' and 'brevo' in c.get('name', '').lower():
      print(c['id']); break
except: pass
" 2>/dev/null)

if [ -z "$BREVO_CRED_ID" ]; then
  echo "  ⚠️  Keine 'Brevo API Key' Credential (HTTP Header Auth) gefunden."
  echo "     Bitte in n8n UI anlegen: Header-Name 'api-key', Wert = BREVO_API_KEY."
  echo "     Siehe docs/N8N_DEPLOYMENT.md. Workflows werden ohne Credential importiert"
  echo "     und müssen danach manuell in der UI verknüpft werden."
else
  echo "  ✅ Brevo Credential ID: $BREVO_CRED_ID"
fi

import_workflow () {
  local file="$1"
  local name
  name=$(python3 -c "import json; print(json.load(open('$file'))['name'])")

  echo ""
  echo "▶ Importiere Workflow: $name"

  local payload
  payload=$(python3 - "$file" "$BREVO_CRED_ID" <<'PYEOF'
import sys, json

path, cred_id = sys.argv[1], sys.argv[2]
with open(path) as f:
    wf = json.load(f)

if cred_id:
    for node in wf.get("nodes", []):
        creds = node.get("credentials", {})
        if "httpHeaderAuth" in creds:
            creds["httpHeaderAuth"]["id"] = cred_id

print(json.dumps(wf))
PYEOF
)

  local result
  result=$(curl -s -b "$COOKIE" -X POST "$N8N/rest/workflows" \
    -H "Content-Type: application/json" \
    -d "$payload")

  local wf_id
  wf_id=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',d).get('id','ERROR'))" 2>/dev/null)

  if [ "$wf_id" = "ERROR" ] || [ -z "$wf_id" ]; then
    echo "  ❌ Import fehlgeschlagen: $result"
  else
    echo "  ✅ Workflow ID: $wf_id (inaktiv importiert - in der UI aktivieren nach Prüfung der Credentials/IDs)"
  fi
}

import_workflow "$SCRIPT_DIR/n8n-workflows/optin-to-brevo.json"
import_workflow "$SCRIPT_DIR/n8n-workflows/welcome-sequence-followup.json"
import_workflow "$SCRIPT_DIR/n8n-workflows/abandoned-cart-followup.json"

echo ""
echo "▶ Webhook-URLs (nach Aktivierung der Workflows):"
echo "  Opt-in:            $N8N/webhook/optin"
echo "  Welcome Followup:  $N8N/webhook/welcome-followup  (wird intern vom Opt-in-Workflow aufgerufen)"
echo "  Abandoned Cart:    $N8N/webhook/cart-abandon"
echo ""
echo "⚠️  Vor dem Aktivieren prüfen:"
echo "  - Brevo-Listen-IDs in den ENV-Vars BREVO_LIST_* gesetzt (docs/N8N_DEPLOYMENT.md)"
echo "  - Brevo-Template-IDs in BREVO_TPL_* gesetzt"
echo "  - Brevo Credential korrekt verknüpft"

rm -f "$COOKIE"
