#!/bin/bash
# ApexCore — Vollständiges Deploy-Script
# Einmalig ausführen: bash <(curl -s https://raw.githubusercontent.com/AIA2025/apexcore/claude/sharp-brahmagupta-03oc5/deploy-all.sh)

set -e
REPO="https://raw.githubusercontent.com/AIA2025/apexcore/claude/sharp-brahmagupta-03oc5"
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'
ok() { echo -e "${GREEN}✅ $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; }
h() { echo -e "\n${BOLD}▶ $1${NC}"; }

h "1) Caddyfile aktualisieren"
CADDY_PATH="/opt/openclaw/reverse-proxy/Caddyfile"
cp "$CADDY_PATH" "${CADDY_PATH}.bak.$(date +%Y%m%d_%H%M%S)" && ok "Backup erstellt"
curl -fsSL "$REPO/Caddyfile" > "$CADDY_PATH" && ok "Caddyfile eingespielt"

docker exec caddy caddy validate --config /etc/caddy/Caddyfile 2>&1 && ok "Config valide" || { err "Caddy Validate fehlgeschlagen — Backup wird wiederhergestellt"; cp "${CADDY_PATH}.bak."* "$CADDY_PATH"; exit 1; }
docker exec caddy caddy reload --config /etc/caddy/Caddyfile && ok "Caddy neu geladen"

h "2) n8n-lx1z (Port 5679) stoppen"
if docker ps -q --filter name=n8n-lx1z | grep -q .; then
  docker stop n8n-lx1z-n8n-1 && ok "n8n-lx1z gestoppt"
else
  ok "n8n-lx1z bereits gestoppt"
fi

h "3) Dashboard aktualisieren (Ports korrigiert)"
curl -fsSL "$REPO/dashboard/index.html" > /opt/apexcore-dashboard/index.html && ok "Dashboard aktualisiert"

h "4) Notion Backup Cronjob einrichten"
CRON_LINE="30 2 * * * /root/scripts/notion-backup.sh >> /root/logs/notion-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -q "notion-backup"; then
  ok "Cronjob bereits vorhanden"
else
  (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab - && ok "Cronjob eingerichtet"
fi

h "5) System-Check"
echo ""
echo "Docker Services:"
docker ps --format "  {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -v "^$"
echo ""
echo "n8n Workflows (Aktivstatus):"
COOKIE=$(mktemp)
curl -s -c "$COOKIE" -X POST http://localhost:5678/rest/login \
  -H "Content-Type: application/json" \
  -d '{"emailOrLdapLoginId":"m.dordevic@apexcore.group","password":"Trustno1981!"}' > /dev/null
for ID in dQhE0mzXP0BlvlKt QR8IldDUDuhRHW7r 8SAHX9kl2oLba5h8; do
  curl -s -b "$COOKIE" http://localhost:5678/rest/workflows/$ID | \
  python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(f'  {\"✅\" if d.get(\"active\") else \"❌\"} {d.get(\"name\")}')" 2>/dev/null
done
rm -f "$COOKIE"

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════╗"
echo "║   ApexCore Deploy abgeschlossen  ║"
echo "║                                  ║"
echo "║  Subdomains (nach DNS-Setup):    ║"
echo "║  openwebui.apexcore.group        ║"
echo "║  n8n.apexcore.group              ║"
echo "║  hermes.apexcore.group           ║"
echo "║  paperclip.apexcore.group        ║"
echo "║  dashboard.apexcore.group        ║"
echo -e "╚══════════════════════════════════╝${NC}"
