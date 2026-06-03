#!/usr/bin/env bash
# install_paperclip_apexcore.sh — Paperclip + Hermes Setup for ApexCore VPS
# Run as root on Ubuntu 22.04/24.04. Node 20+, pnpm 9+ required.
set -euo pipefail

PAPERCLIP_PORT=3100
HERMES_PORT=7071
PAPERCLIP_DATA_DIR=/opt/paperclip/data
HERMES_DIR=/opt/apexcore/hermes
REPO_RAW="https://raw.githubusercontent.com/AIA2025/ApexCore-Group/main"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ─── 0. Prerequisites ─────────────────────────────────────────────────────────
info "Checking prerequisites..."

if ! command -v node &>/dev/null; then
  info "Installing Node.js 20 via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

NODE_MAJOR=$(node --version | grep -oP '(?<=v)\d+')
[[ $NODE_MAJOR -ge 20 ]] || die "Node.js 20+ required (got $(node --version))"

if ! command -v pnpm &>/dev/null; then
  info "Installing pnpm 9..."
  npm install -g pnpm@9
fi

PNPM_MAJOR=$(pnpm --version | cut -d. -f1)
[[ $PNPM_MAJOR -ge 9 ]] || die "pnpm 9+ required (got $(pnpm --version))"

info "Node $(node --version) / pnpm $(pnpm --version) — OK"

# ─── 1. Install Paperclip ────────────────────────────────────────────────────
info "Installing @paperclipai/server@0.3.1..."
npm install -g @paperclipai/server@0.3.1

mkdir -p "$PAPERCLIP_DATA_DIR"

# ─── 2. systemd unit: paperclip ──────────────────────────────────────────────
info "Writing paperclip.service..."
cat > /etc/systemd/system/paperclip.service <<EOF
[Unit]
Description=Paperclip Control Plane
After=network.target

[Service]
Type=simple
ExecStart=$(which paperclip) start --port ${PAPERCLIP_PORT} --data-dir ${PAPERCLIP_DATA_DIR}
Restart=always
RestartSec=5
Environment=NODE_ENV=production
WorkingDirectory=${PAPERCLIP_DATA_DIR}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable paperclip
systemctl restart paperclip
info "Paperclip service started. Waiting for health check..."

for i in {1..30}; do
  if curl -sf "http://127.0.0.1:${PAPERCLIP_PORT}/api/health" | grep -q '"ok"'; then
    info "Paperclip is healthy ✅"
    break
  fi
  [[ $i -eq 30 ]] && die "Paperclip did not become healthy after 30s"
  sleep 1
done

# ─── 3. Deploy Hermes Dispatcher ─────────────────────────────────────────────
info "Deploying Hermes Dispatcher..."
mkdir -p "$HERMES_DIR"

curl -fsSL "${REPO_RAW}/hermes/dispatcher.js"   > "${HERMES_DIR}/dispatcher.js"
curl -fsSL "${REPO_RAW}/hermes/package.json"     > "${HERMES_DIR}/package.json"
curl -fsSL "${REPO_RAW}/hermes/hermes.service"   > /etc/systemd/system/hermes.service

cd "$HERMES_DIR" && npm install --omit=dev

APEXCORE_ENV="/etc/apexcore/hermes.env"
mkdir -p /etc/apexcore
if [[ -z "${DISPATCHER_TOKEN:-}" ]]; then
  if [[ -f "$APEXCORE_ENV" ]] && grep -q "^DISPATCHER_TOKEN=" "$APEXCORE_ENV" 2>/dev/null; then
    DISPATCHER_TOKEN=$(grep "^DISPATCHER_TOKEN=" "$APEXCORE_ENV" | cut -d= -f2-)
    info "Using existing DISPATCHER_TOKEN from ${APEXCORE_ENV}"
  else
    warn "DISPATCHER_TOKEN not set — generating a random token."
    DISPATCHER_TOKEN=$(openssl rand -hex 32)
  fi
fi
echo "DISPATCHER_TOKEN=${DISPATCHER_TOKEN}" > "$APEXCORE_ENV"
chmod 600 "$APEXCORE_ENV"
info "DISPATCHER_TOKEN saved to ${APEXCORE_ENV}"

systemctl daemon-reload
systemctl enable hermes
systemctl restart hermes
info "Hermes Dispatcher started ✅"

# ─── 4. Seed Paperclip (company, agent, projects, issues) ────────────────────
info "Seeding Paperclip knowledge layer..."

BASE="http://127.0.0.1:${PAPERCLIP_PORT}/api"

# Create company
COMPANY=$(curl -sf -X POST "${BASE}/companies" \
  -H "Content-Type: application/json" \
  -d '{"name":"ApexCore Multi-Agent Company","description":"Control Plane for the ApexCore multi-agent system. Prefix: APE.","prefix":"APE"}')
COMPANY_ID=$(echo "$COMPANY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Company created: ${COMPANY_ID}"

# Register Hermes Dispatcher agent
HERMES_HOST="${HERMES_HOST:-127.0.0.1}"
AGENT=$(curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/agents" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Hermes Dispatcher\",
    \"description\": \"HTTP execution layer. Routes Paperclip dispatch calls to Claude Code, VPS workloads, and tools.\",
    \"adapterType\": \"http\",
    \"adapterConfig\": {
      \"url\": \"http://${HERMES_HOST}:${HERMES_PORT}/dispatch\",
      \"method\": \"POST\",
      \"headers\": { \"Authorization\": \"Bearer \${DISPATCHER_TOKEN}\" },
      \"payloadTemplate\": { \"source\": \"paperclip\", \"kind\": \"dispatch\" },
      \"timeoutSec\": 30
    },
    \"runtimeConfig\": {
      \"heartbeat\": { \"enabled\": true, \"intervalSec\": 60 }
    },
    \"metadata\": {
      \"healthUrl\": \"http://${HERMES_HOST}:${HERMES_PORT}/health\",
      \"dispatchUrl\": \"http://${HERMES_HOST}:${HERMES_PORT}/dispatch\"
    }
  }")
AGENT_ID=$(echo "$AGENT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
info "Agent 'Hermes Dispatcher' created: ${AGENT_ID}"

# ─── Projects (Knowledge Folders) ────────────────────────────────────────────
declare -A PROJECTS
create_project() {
  local NAME="$1" DESC="$2"
  local RESULT
  RESULT=$(curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/projects" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${NAME}\",\"description\":\"${DESC}\"}")
  echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
}

PROJECTS[00]=$(create_project "00-Runbooks"       "Dispatcher-, Orchestrierungs- und Recovery-Runbooks")
PROJECTS[01]=$(create_project "01-Infra"          "VPS, Docker, Netzwerk, Postgres, Backups")
PROJECTS[02]=$(create_project "02-Products"       "Produkt-Blueprints, Digital-Product-Specs")
PROJECTS[03]=$(create_project "03-Sales"          "GTM, Pricing, Outreach, Content-Repurposing")
PROJECTS[04]=$(create_project "04-Legal-AI-Act"   "AI-Act, Compliance, Banking, Data Governance")
PROJECTS[05]=$(create_project "05-Sync-Briefings" "Cross-Agent-Sync zwischen den Apex-Agenten")
PROJECTS[06]=$(create_project "06-Templates"      "Command-JSON, Runbook-Skeletons, Doc-Stubs")

for k in "${!PROJECTS[@]}"; do
  info "Project ${k} created: ${PROJECTS[$k]}"
done

# ─── Issue stubs (APE-1 … APE-7) ─────────────────────────────────────────────
create_issue() {
  local PROJ_ID="$1" TITLE="$2" BODY="$3"
  curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/issues" \
    -H "Content-Type: application/json" \
    -d "{\"projectId\":\"${PROJ_ID}\",\"title\":\"${TITLE}\",\"body\":\"${BODY}\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('key','?'), d.get('id','?'))"
}

APE1=$(create_issue "${PROJECTS[00]}" "APE-1 Runbook Index" \
  "Sammelpunkt für alle Runbooks.\n\nDokumente:\n- HERMESFLOWTECHNICALV1.md\n- RUNBOOKORCHESTRATIONV1.md\n- Dispatcher-Runbook (Env, Ports, Token)")

APE2=$(create_issue "${PROJECTS[01]}" "APE-2 Infra Overview" \
  "VPS-Topologie, Docker-Stack, Netzwerk-Layout.\n\n- Host: 76.13.138.73\n- Dienste: Caddy, Paperclip :3100, Hermes :7071, cmd-api :7070\n- Tailscale für Remote-Zugriff empfohlen")

APE3=$(create_issue "${PROJECTS[02]}" "APE-3 Product Blueprints" \
  "Produkt-Blueprints und Digital-Product-Specs für ApexCore.\n\nPlatzhalter — Inhalte folgen aus GTM-Briefing.")

APE4=$(create_issue "${PROJECTS[03]}" "APE-4 GTM & Sales" \
  "GTM-Strategie, Pricing-Modelle, Content-Repurposing-Pipeline.\n\nPlatzhalter — Inhalte folgen aus Sales-Briefing.")

APE5=$(create_issue "${PROJECTS[04]}" "APE-5 Legal & AI-Act" \
  "EU-AI-Act Compliance, Banking-Regulatorik, Data Governance.\n\nPlatzhalter — Inhalte folgen aus Legal-Briefing.")

APE6=$(create_issue "${PROJECTS[05]}" "APE-6 Sync-Briefing Template" \
  "Wiederkehrendes Cross-Agent-Briefing (Hermes / Claude / Perplexity).\n\nRhythmus: täglich oder auf Trigger.\nFormat: Structured JSON → /dispatch")

APE7=$(create_issue "${PROJECTS[06]}" "APE-7 Command-JSON Template" \
  'Wiederverwendbares Dispatch-Template:\n\n```json\n{\n  "source": "paperclip",\n  "kind": "dispatch",\n  "agentId": "<agent-id>",\n  "runId": "<run-uuid>",\n  "context": {\n    "goal": "",\n    "project": "",\n    "input": ""\n  }\n}\n```')

info "Issues created: APE-1=${APE1} APE-2=${APE2} APE-3=${APE3} APE-4=${APE4} APE-5=${APE5} APE-6=${APE6} APE-7=${APE7}"

# ─── 5. Adapter health test ───────────────────────────────────────────────────
info "Running adapter health probe..."
PROBE=$(curl -sf -X POST \
  "${BASE}/companies/${COMPANY_ID}/adapters/http/test-environment" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"http://${HERMES_HOST}:${HERMES_PORT}/dispatch\",\"method\":\"POST\",\"headers\":{\"Authorization\":\"Bearer ${DISPATCHER_TOKEN}\"},\"timeoutSec\":10}" \
  || echo '{"status":"probe-failed"}')
info "Adapter probe result: ${PROBE}"

# ─── 6. Print summary ─────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ApexCore × Paperclip — Setup complete"
echo "══════════════════════════════════════════════════════════"
echo "  Paperclip UI  : http://127.0.0.1:${PAPERCLIP_PORT}"
echo "  Company ID    : ${COMPANY_ID}"
echo "  Agent ID      : ${AGENT_ID}"
echo "  Hermes health : http://${HERMES_HOST}:${HERMES_PORT}/health"
echo ""
echo "  NEXT STEPS:"
echo "  1. Store DISPATCHER_TOKEN as a Company Secret in Paperclip"
echo "  2. Enable Tailscale and run: paperclip start --bind tailnet"
echo "  3. Build UI: pnpm build  (in @paperclipai/server package dir)"
echo "  4. Upload docs to APE-1: HERMESFLOWTECHNICALV1.md, RUNBOOKORCHESTRATIONV1.md"
echo "══════════════════════════════════════════════════════════"
