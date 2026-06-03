#!/bin/bash
# ApexCore — Vollständiges Deploy-Script
# Einmalig ausführen: bash <(curl -s https://raw.githubusercontent.com/AIA2025/apexcore/claude/sharp-brahmagupta-03oc5/deploy-all.sh)

REPO="https://raw.githubusercontent.com/AIA2025/apexcore/claude/sharp-brahmagupta-03oc5"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

# Env laden – einmalig ganz oben, damit alle Sections davon profitieren
ENV_FILE="/root/.apexcore.env"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}▶ $1${NC}"; }

# ─── 1) Caddyfile ────────────────────────────────────────────────────────────
h "1) Caddyfile aktualisieren"
CADDY_PATH="/opt/openclaw/reverse-proxy/Caddyfile"
mkdir -p "$(dirname "$CADDY_PATH")"
cp "$CADDY_PATH" "${CADDY_PATH}.bak.$(date +%Y%m%d_%H%M%S)" 2>/dev/null && ok "Backup erstellt" || warn "Kein Backup (Datei neu)"
curl -fsSL "$REPO/Caddyfile" > "$CADDY_PATH" && ok "Caddyfile eingespielt"

if docker exec caddy caddy validate --config /etc/caddy/Caddyfile 2>/dev/null; then
  ok "Config valide"
  docker exec caddy caddy reload --config /etc/caddy/Caddyfile && ok "Caddy neu geladen" || err "Caddy reload fehlgeschlagen"
else
  err "Caddy validate fehlgeschlagen"
fi

# ─── 2) n8n-lx1z stoppen ─────────────────────────────────────────────────────
h "2) n8n-lx1z (alten Port 5679) stoppen"
docker stop n8n-lx1z-n8n-1 2>/dev/null && ok "n8n-lx1z gestoppt" || ok "n8n-lx1z bereits gestoppt"

# ─── 3) Dashboard ─────────────────────────────────────────────────────────────
h "3) Dashboard aktualisieren"
mkdir -p /opt/apexcore-dashboard
curl -fsSL "$REPO/dashboard/index.html" > /opt/apexcore-dashboard/index.html && ok "Dashboard aktualisiert"

# ─── 4) cmd-api (Port 7070) ───────────────────────────────────────────────────
h "4) cmd-api starten"
mkdir -p /opt/apexcore/cmd-api
curl -fsSL "$REPO/cmd-api/server.py" > /opt/apexcore/cmd-api/server.py && ok "cmd-api heruntergeladen"
pkill -f "cmd-api/server.py" 2>/dev/null || true
sleep 1
if [ -z "$CMD_API_TOKEN" ]; then
  CMD_API_TOKEN=$(openssl rand -hex 32)
  # Kein Duplikat anhängen falls Key bereits existiert
  if ! grep -q "^CMD_API_TOKEN=" "$ENV_FILE" 2>/dev/null; then
    echo "CMD_API_TOKEN=$CMD_API_TOKEN" >> "$ENV_FILE"
  else
    sed -i "s|^CMD_API_TOKEN=.*|CMD_API_TOKEN=$CMD_API_TOKEN|" "$ENV_FILE"
  fi
  ok "Neues CMD_API_TOKEN generiert und gespeichert in $ENV_FILE"
else
  ok "CMD_API_TOKEN bereits gesetzt"
fi
CMD_TOKEN="$CMD_API_TOKEN" nohup python3 /opt/apexcore/cmd-api/server.py > /var/log/cmd-api.log 2>&1 &
sleep 1
kill -0 $! 2>/dev/null && ok "cmd-api läuft (PID $!)" || warn "cmd-api start unsicher"

# ─── 5) Porkbun DNS Records ───────────────────────────────────────────────────
h "5) DNS Records (Porkbun)"
DOMAIN="apexcore.group"
VPS_IP="76.13.138.73"

# Only proceed if keys are available in ENV_FILE or environment
if [ -z "$PORKBUN_APIKEY" ] || [ -z "$PORKBUN_SECRETKEY" ]; then
  if [ -t 0 ]; then
    echo ""
    echo -e "${YELLOW}Porkbun API Keys werden benötigt.${NC}"
    echo "Du findest sie unter: porkbun.com → Account → API Access"
    echo ""
    read -r -p "  Porkbun API Key (pk1_...):    " PORKBUN_APIKEY
    read -r -p "  Porkbun Secret Key (sk1_...): " PORKBUN_SECRETKEY
    echo ""

    if [ -n "$PORKBUN_APIKEY" ] && [ -n "$PORKBUN_SECRETKEY" ]; then
      grep -v "PORKBUN_" "$ENV_FILE" 2>/dev/null > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE" || true
      echo "PORKBUN_APIKEY=$PORKBUN_APIKEY" >> "$ENV_FILE"
      echo "PORKBUN_SECRETKEY=$PORKBUN_SECRETKEY" >> "$ENV_FILE"
      ok "Keys gespeichert in $ENV_FILE"
    fi
  else
    warn "Nicht-interaktiver Modus — DNS-Prompt übersprungen (Keys aus ENV verwenden)"
  fi
fi

if [ -n "$PORKBUN_APIKEY" ] && [ -n "$PORKBUN_SECRETKEY" ]; then
  echo "  Pinge Porkbun API..."
  PING=$(curl -s -X POST "https://api.porkbun.com/api/json/v3/ping" \
    -H "Content-Type: application/json" \
    -d "{\"apikey\":\"$PORKBUN_APIKEY\",\"secretapikey\":\"$PORKBUN_SECRETKEY\"}")

  if echo "$PING" | grep -q '"status":"SUCCESS"'; then
    ok "Porkbun API erreichbar"
    for SUB in n8n openwebui hermes dashboard paperclip; do
      R=$(curl -s -X POST "https://api.porkbun.com/api/json/v3/dns/create/$DOMAIN" \
        -H "Content-Type: application/json" \
        -d "{\"apikey\":\"$PORKBUN_APIKEY\",\"secretapikey\":\"$PORKBUN_SECRETKEY\",\"name\":\"$SUB\",\"type\":\"A\",\"content\":\"$VPS_IP\",\"ttl\":\"300\"}")
      if echo "$R" | grep -q '"status":"SUCCESS"'; then
        ok "DNS: $SUB.$DOMAIN → $VPS_IP"
      else
        STATUS=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('message','?'))" 2>/dev/null)
        warn "DNS $SUB: $STATUS"
      fi
    done
  else
    err "Porkbun API fehlgeschlagen — Keys prüfen"
  fi
else
  warn "DNS übersprungen (keine Keys angegeben)"
  echo ""
  echo "  DNS manuell in Porkbun hinzufügen (porkbun.com → apexcore.group → DNS):"
  for SUB in n8n openwebui hermes dashboard paperclip; do
    echo "    $SUB  →  A  →  $VPS_IP"
  done
fi

# ─── 5b) Product 4 — Bitcoin Tax Kit ─────────────────────────────────────────
h "5b) Product 4 — Bitcoin Tax \u0026 Reporting Kit"
P4_BASE="/data/apex-core-central/output/product_4"
P4_MD="$P4_BASE/markdown/bitcoin-tax-reporting-kit.md"
P4_PDF="$P4_BASE/final/bitcoin-tax-reporting-kit.pdf"
P4_WEB="/opt/apexcore-products/product_4"

mkdir -p "$P4_BASE/markdown" "$P4_BASE/final" "$P4_WEB"

# Deploy markdown + product page from repo
curl -fsSL "$REPO/products/product_4/bitcoin-tax-reporting-kit.md" > "$P4_MD" && ok "Bitcoin Tax Kit markdown gespeichert"
curl -fsSL "$REPO/products/product_4/index.html" > "$P4_WEB/index.html" && ok "Product 4 Seite deployed"

# Install pandoc if needed and build PDF
if ! command -v pandoc >/dev/null; then
  warn "pandoc nicht gefunden — installiere..."
  apt-get update -qq && apt-get install -y -qq pandoc wkhtmltopdf 2>/dev/null && ok "pandoc installiert" || warn "pandoc Install fehlgeschlagen — PDF-Build übersprungen"
fi

# Deploy build-kit.sh script
curl -fsSL "$REPO/scripts/build-kit.sh" > /usr/local/bin/build-kit.sh && chmod +x /usr/local/bin/build-kit.sh && ok "build-kit.sh installiert"

# Build PDF
if command -v pandoc >/dev/null && [ -f "$P4_MD" ]; then
  pandoc "$P4_MD" \
    --pdf-engine=wkhtmltopdf \
    --toc --toc-depth=2 \
    -V margin-top=25mm -V margin-bottom=25mm \
    -V margin-left=20mm -V margin-right=20mm \
    -V fontsize=11pt -V papersize=a4 \
    -o "$P4_PDF" 2>/var/log/apexcore-build.log && \
    ok "PDF erzeugt: $P4_PDF ($(du -h "$P4_PDF" | cut -f1))" || \
    warn "PDF-Build fehlgeschlagen — Log: /var/log/apexcore-build.log"
else
  warn "PDF-Build übersprungen (pandoc fehlt oder Markdown nicht gefunden)"
fi

# ─── 6) Notion Backup Cronjob ─────────────────────────────────────────────────
h "6) Notion Backup Cronjob"
CRON_LINE="30 2 * * * /root/scripts/notion-backup.sh >> /root/logs/notion-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -q "notion-backup"; then
  ok "Cronjob bereits vorhanden"
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab - && ok "Cronjob eingerichtet"
fi

# ─── 7) System-Check ──────────────────────────────────────────────────────────
h "7) System-Check"

echo ""
echo "Docker Services:"
docker ps --format "  {{.Names}}\t{{.Status}}" | head -15


echo ""
echo "n8n Workflows:"
if [ -z "$N8N_PASSWORD" ]; then
  warn "N8N_PASSWORD nicht gesetzt — Workflow-Status übersprungen"
else
  COOKIE=$(mktemp)
  curl -s -c "$COOKIE" -X POST http://localhost:5678/rest/login \
    -H "Content-Type: application/json" \
    -d '{"emailOrLdapLoginId":"m.dordevic@apexcore.group","password":"'"$N8N_PASSWORD"'"}' >/dev/null
  for ID in r5mG8kn5w9zUMIiL QR8IldDUDuhRHW7r 8SAHX9kl2oLba5h8 1KQuPEzLqSL8Dqs9; do
    curl -s -b "$COOKIE" http://localhost:5678/rest/workflows/$ID 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(f'  {\"✅\" if d.get(\"active\") else \"❌\"} {d.get(\"name\",\"?\")}')" 2>/dev/null || true
  done
  rm -f "$COOKIE"
fi

echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════╗"
echo "║   ApexCore Deploy abgeschlossen       ║"
echo "╠═══════════════════════════════════════╣"
echo "║  oc.apexcore.group      → OpenClaw   ║"
echo "║  n8n.apexcore.group     → n8n        ║"
echo "║  openwebui.apexcore.group → Open UI  ║"
echo "║  dashboard.apexcore.group → Dashboard ║"
echo "║  hermes.apexcore.group  → Hermes     ║"
echo "║  paperclip.apexcore.group → Paperclip ║"
echo -e "╚═══════════════════════════════════════╝${NC}"
