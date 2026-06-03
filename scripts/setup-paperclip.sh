#!/usr/bin/env bash
# scripts/setup-paperclip.sh — Install & start Paperclip on VPS
# Called by cmd-api run_deploy(). Idempotent.
set -euo pipefail

LOG="${1:-/var/log/paperclip-setup.log}"
exec >> "$LOG" 2>&1

echo "[$(date -u +%FT%TZ)] === Paperclip setup ==="

# Node.js 20+
if ! command -v node &>/dev/null || [[ $(node --version | grep -oP '(?<=v)\d+') -lt 20 ]]; then
  echo "Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
  apt-get install -y nodejs >/dev/null
fi

# pnpm 9+
if ! command -v pnpm &>/dev/null; then
  npm install -g pnpm@9 --quiet
fi

# @paperclipai/server
if ! command -v paperclip &>/dev/null; then
  echo "Installing @paperclipai/server@0.3.1..."
  npm install -g @paperclipai/server@0.3.1 --quiet
fi

PAPERCLIP_DATA=/opt/paperclip/data
mkdir -p "$PAPERCLIP_DATA"

# Write systemd service
cat > /etc/systemd/system/paperclip.service <<'SVC'
[Unit]
Description=Paperclip Control Plane
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/paperclip start --port 3100 --data-dir /opt/paperclip/data
Restart=always
RestartSec=5
Environment=NODE_ENV=production
WorkingDirectory=/opt/paperclip/data

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable paperclip

if ! systemctl is-active --quiet paperclip; then
  systemctl start paperclip
  echo "Paperclip started."
fi

# Wait for health
for i in {1..20}; do
  if curl -sf http://127.0.0.1:3100/api/health | grep -q '"ok"'; then
    echo "Paperclip healthy after ${i}s."
    break
  fi
  [[ $i -eq 20 ]] && { echo "Paperclip health timeout."; exit 1; }
  sleep 1
done

# Seed only once (check if company exists)
EXISTING=$(curl -sf http://127.0.0.1:3100/api/companies | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [[ "$EXISTING" == "0" ]]; then
  echo "Seeding Paperclip knowledge layer..."
  BASE="http://127.0.0.1:3100/api"
  HERMES_HOST="${HERMES_HOST:-127.0.0.1}"
  HERMES_PORT="${HERMES_PORT:-7071}"

  jq_get() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

  COMPANY=$(curl -sf -X POST "$BASE/companies" \
    -H "Content-Type: application/json" \
    -d '{"name":"ApexCore Multi-Agent Company","description":"Control Plane. Prefix: APE.","prefix":"APE"}')
  CID=$(echo "$COMPANY" | jq_get "['id']")
  echo "Company: $CID"

  curl -sf -X POST "$BASE/companies/$CID/agents" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"Hermes Dispatcher\",\"description\":\"HTTP execution layer — routes dispatch calls to Claude Code, VPS workloads and tools.\",\"adapterType\":\"http\",\"adapterConfig\":{\"url\":\"http://${HERMES_HOST}:${HERMES_PORT}/dispatch\",\"method\":\"POST\",\"headers\":{\"Authorization\":\"Bearer \${DISPATCHER_TOKEN}\"},\"payloadTemplate\":{\"source\":\"paperclip\",\"kind\":\"dispatch\"},\"timeoutSec\":30},\"runtimeConfig\":{\"heartbeat\":{\"enabled\":true,\"intervalSec\":60}},\"metadata\":{\"healthUrl\":\"http://${HERMES_HOST}:${HERMES_PORT}/health\"}}" \
    | jq_get "['id']" | xargs echo "Agent Hermes:"

  mk_proj() { curl -sf -X POST "$BASE/companies/$CID/projects" -H "Content-Type: application/json" -d "{\"name\":\"$1\",\"description\":\"$2\"}" | jq_get "['id']"; }
  mk_issue() { curl -sf -X POST "$BASE/companies/$CID/issues" -H "Content-Type: application/json" -d "{\"projectId\":\"$1\",\"title\":\"$2\",\"body\":\"$3\"}" | jq_get "['key']"; }

  P00=$(mk_proj "00-Runbooks"       "Dispatcher-, Orchestrierungs- und Recovery-Runbooks")
  P01=$(mk_proj "01-Infra"          "VPS, Docker, Netzwerk, Postgres, Backups")
  P02=$(mk_proj "02-Products"       "Produkt-Blueprints, Digital-Product-Specs")
  P03=$(mk_proj "03-Sales"          "GTM, Pricing, Outreach, Content-Repurposing")
  P04=$(mk_proj "04-Legal-AI-Act"   "AI-Act, Compliance, Banking, Data Governance")
  P05=$(mk_proj "05-Sync-Briefings" "Cross-Agent-Sync zwischen den Apex-Agenten")
  P06=$(mk_proj "06-Templates"      "Command-JSON, Runbook-Skeletons, Doc-Stubs")

  mk_issue "$P00" "APE-1 Runbook Index"         "HERMESFLOWTECHNICALV1.md + RUNBOOKORCHESTRATIONV1.md"
  mk_issue "$P01" "APE-2 Infra Overview"        "VPS 76.13.138.73 · Caddy · Paperclip :3100 · Hermes :7071 · cmd-api :7070"
  mk_issue "$P02" "APE-3 Product Blueprints"    "Produkt-Blueprints für ApexCore"
  mk_issue "$P03" "APE-4 GTM & Sales"           "GTM-Strategie, Pricing, Content-Repurposing"
  mk_issue "$P04" "APE-5 Legal & AI-Act"        "EU-AI-Act, Compliance, Banking, Data Governance"
  mk_issue "$P05" "APE-6 Sync-Briefing"         "Cross-Agent-Briefing Hermes / Claude / Perplexity"
  mk_issue "$P06" "APE-7 Command-JSON Template" "Wiederverwendbares Dispatch-Template"

  echo "Seeding complete. Company=$CID"
else
  echo "Paperclip already seeded ($EXISTING companies). Skipping."
fi

echo "[$(date -u +%FT%TZ)] === Paperclip setup done ==="
