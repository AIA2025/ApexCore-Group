#!/usr/bin/env bash
# paperclip/seed.sh — Standalone re-seed script for Paperclip knowledge layer.
# Run after Paperclip is already running to re-create company, agent, projects,
# and issue stubs from scratch (idempotent on a fresh instance).
set -euo pipefail

BASE="${PAPERCLIP_BASE_URL:-http://127.0.0.1:3100/api}"
HERMES_HOST="${HERMES_HOST:-127.0.0.1}"
HERMES_PORT="${HERMES_PORT:-7071}"
DISPATCHER_TOKEN="${DISPATCHER_TOKEN:?DISPATCHER_TOKEN env var required}"

jq_get() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }

wait_healthy() {
  for i in {1..20}; do
    curl -sf "${BASE}/health" | grep -q '"ok"' && return 0
    sleep 1
  done
  echo "Paperclip not healthy at ${BASE}" >&2; exit 1
}

wait_healthy
echo "[seed] Paperclip healthy"

# Company
COMPANY=$(curl -sf -X POST "${BASE}/companies" \
  -H "Content-Type: application/json" \
  -d '{"name":"ApexCore Multi-Agent Company","description":"Control Plane for the ApexCore multi-agent system. Prefix: APE.","prefix":"APE"}')
COMPANY_ID=$(echo "$COMPANY" | jq_get "['id']")
echo "[seed] Company: ${COMPANY_ID}"

# Agent
curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/agents" \
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
    \"runtimeConfig\": { \"heartbeat\": { \"enabled\": true, \"intervalSec\": 60 } },
    \"metadata\": {
      \"healthUrl\": \"http://${HERMES_HOST}:${HERMES_PORT}/health\",
      \"dispatchUrl\": \"http://${HERMES_HOST}:${HERMES_PORT}/dispatch\"
    }
  }" | jq_get "['id']" | xargs -I{} echo "[seed] Agent Hermes: {}"

# Projects
mk_proj() {
  curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/projects" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$1\",\"description\":\"$2\"}" | jq_get "['id']"
}

P00=$(mk_proj "00-Runbooks"       "Dispatcher-, Orchestrierungs- und Recovery-Runbooks")
P01=$(mk_proj "01-Infra"          "VPS, Docker, Netzwerk, Postgres, Backups")
P02=$(mk_proj "02-Products"       "Produkt-Blueprints, Digital-Product-Specs")
P03=$(mk_proj "03-Sales"          "GTM, Pricing, Outreach, Content-Repurposing")
P04=$(mk_proj "04-Legal-AI-Act"   "AI-Act, Compliance, Banking, Data Governance")
P05=$(mk_proj "05-Sync-Briefings" "Cross-Agent-Sync zwischen den Apex-Agenten")
P06=$(mk_proj "06-Templates"      "Command-JSON, Runbook-Skeletons, Doc-Stubs")

echo "[seed] Projects: 00=${P00} 01=${P01} 02=${P02} 03=${P03} 04=${P04} 05=${P05} 06=${P06}"

# Issues
mk_issue() {
  curl -sf -X POST "${BASE}/companies/${COMPANY_ID}/issues" \
    -H "Content-Type: application/json" \
    -d "{\"projectId\":\"$1\",\"title\":\"$2\",\"body\":\"$3\"}" \
    | jq_get "['key']"
}

mk_issue "$P00" "APE-1 Runbook Index" \
  "Sammelpunkt für alle Runbooks.\n\nDokumente:\n- HERMESFLOWTECHNICALV1.md\n- RUNBOOKORCHESTRATIONV1.md\n- Dispatcher-Runbook (Env, Ports, Token)" | xargs echo "[seed] APE-1:"

mk_issue "$P01" "APE-2 Infra Overview" \
  "VPS-Topologie, Docker-Stack.\n\n- Host: 76.13.138.73\n- Dienste: Caddy, Paperclip :3100, Hermes :7071, cmd-api :7070\n- Tailscale für Remote-Zugriff empfohlen" | xargs echo "[seed] APE-2:"

mk_issue "$P02" "APE-3 Product Blueprints" \
  "Produkt-Blueprints und Digital-Product-Specs für ApexCore." | xargs echo "[seed] APE-3:"

mk_issue "$P03" "APE-4 GTM & Sales" \
  "GTM-Strategie, Pricing-Modelle, Content-Repurposing-Pipeline." | xargs echo "[seed] APE-4:"

mk_issue "$P04" "APE-5 Legal & AI-Act" \
  "EU-AI-Act Compliance, Banking-Regulatorik, Data Governance." | xargs echo "[seed] APE-5:"

mk_issue "$P05" "APE-6 Sync-Briefing Template" \
  "Wiederkehrendes Cross-Agent-Briefing (Hermes / Claude / Perplexity).\n\nRhythmus: täglich oder auf Trigger.\nFormat: Structured JSON → /dispatch" | xargs echo "[seed] APE-6:"

mk_issue "$P06" "APE-7 Command-JSON Template" \
  "Wiederverwendbares Dispatch-Template. Siehe docs/command-template.json." | xargs echo "[seed] APE-7:"

echo "[seed] Done. COMPANY_ID=${COMPANY_ID}"
