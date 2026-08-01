#!/bin/bash
# Hermes Desktop → VPS Migration
# Überträgt ~/.hermes (Config, Skills, Memories, Sessions, Cron) vom iMac
# in den bereits laufenden Server-Container hermes-webui-cxlp-hermes-agent-1.
# Nichts wird gelöscht — es werden vor jedem Schritt Backups angelegt.
#
# WICHTIG: Dieses Skript läuft AUF DEM iMAC (nicht auf dem VPS), da es
# den lokalen ~/.hermes Ordner braucht und deinen SSH-Key nutzt, der
# bereits in Hostinger für den VPS hinterlegt ist.
#
# Ausführen:
#   bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/hermes-desktop-troubleshoot-2ynwwu/hermes/hermes-vps-migrate.sh)
#
# Optional mit Telegram-Token-Fix in einem Rutsch:
#   TELEGRAM_TOKEN=xxx bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/hermes-desktop-troubleshoot-2ynwwu/hermes/hermes-vps-migrate.sh)

set -uo pipefail

VPS_HOST="${VPS_HOST:-76.13.138.73}"
VPS_USER="${VPS_USER:-root}"
CONTAINER="${CONTAINER:-hermes-webui-cxlp-hermes-agent-1}"
LOCAL_HERMES="$HOME/.hermes"
TS=$(date +%Y%m%d_%H%M%S)
WORKDIR="$HOME/Desktop/hermes-migration"
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}▶ $1${NC}"; }

mkdir -p "$WORKDIR"

echo -e "${BOLD}╔══════════════════════════════════════════╗"
echo    "║  Hermes Desktop → VPS Migration          ║"
echo -e "╚══════════════════════════════════════════╝${NC}"

# ── 0. Voraussetzungen ────────────────────────────────────────────────────
h "0) Voraussetzungen prüfen"
[ -d "$LOCAL_HERMES" ] || { err "Lokaler Ordner $LOCAL_HERMES nicht gefunden — Migration nicht möglich"; exit 1; }
ok "Lokaler Hermes-Ordner gefunden: $LOCAL_HERMES"

if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "${VPS_USER}@${VPS_HOST}" "echo ok" >/dev/null 2>&1; then
  err "SSH zum VPS fehlgeschlagen. Teste manuell: ssh ${VPS_USER}@${VPS_HOST}"
  err "Ist dein Public Key (cat ~/.ssh/id_ed25519.pub) in Hostinger unter SSH keys hinterlegt?"
  exit 1
fi
ok "SSH zum VPS ($VPS_HOST) funktioniert"

# ── 1. Lokales Backup ─────────────────────────────────────────────────────
h "1) Lokales Hermes-Backup (Sicherheitsnetz)"
LOCAL_BACKUP="$WORKDIR/imac-hermes-backup-$TS.tar.gz"
tar -czf "$LOCAL_BACKUP" -C "$HOME" .hermes
ok "Lokales Backup: $LOCAL_BACKUP ($(du -h "$LOCAL_BACKUP" | cut -f1))"

# ── 2. Container prüfen ───────────────────────────────────────────────────
h "2) Container auf dem VPS prüfen"
if ! ssh "${VPS_USER}@${VPS_HOST}" "docker inspect $CONTAINER >/dev/null 2>&1"; then
  err "Container '$CONTAINER' nicht gefunden — Migration abgebrochen"
  ssh "${VPS_USER}@${VPS_HOST}" "docker ps --format '{{.Names}}'" | sed 's/^/   Verfügbar: /'
  exit 1
fi
ok "Container '$CONTAINER' existiert auf dem VPS"

REMOTE_HERMES_PATH=$(ssh "${VPS_USER}@${VPS_HOST}" \
  "docker inspect $CONTAINER --format '{{range .Mounts}}{{if eq .Destination \"/home/hermes/.hermes\"}}{{.Source}}{{end}}{{end}}'" 2>/dev/null)

if [ -z "$REMOTE_HERMES_PATH" ]; then
  warn "Kein Bind-Mount für /home/hermes/.hermes gefunden — nutze docker cp Fallback"
  USE_DOCKER_CP=true
else
  ok "Bind-Mount gefunden: $REMOTE_HERMES_PATH"
  USE_DOCKER_CP=false
fi

# ── 3. VPS-seitiges Backup ────────────────────────────────────────────────
h "3) VPS-Backup des bestehenden Container-Zustands (Sicherheitsnetz)"
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p /root/backups"
if [ "$USE_DOCKER_CP" = false ]; then
  ssh "${VPS_USER}@${VPS_HOST}" \
    "tar -czf /root/backups/vps-hermes-pre-migration-$TS.tar.gz -C \"$(dirname "$REMOTE_HERMES_PATH")\" \"$(basename "$REMOTE_HERMES_PATH")\"" \
    && ok "VPS-Backup erstellt: /root/backups/vps-hermes-pre-migration-$TS.tar.gz" \
    || warn "VPS-Backup fehlgeschlagen (evtl. leerer Ordner) — fahre fort"
else
  ssh "${VPS_USER}@${VPS_HOST}" \
    "docker exec $CONTAINER tar -czf /tmp/pre-migration-$TS.tar.gz -C /home/hermes .hermes 2>/dev/null && docker cp $CONTAINER:/tmp/pre-migration-$TS.tar.gz /root/backups/vps-hermes-pre-migration-$TS.tar.gz" \
    && ok "VPS-Backup erstellt (via docker cp): /root/backups/vps-hermes-pre-migration-$TS.tar.gz" \
    || warn "VPS-Backup fehlgeschlagen (evtl. leerer Ordner) — fahre fort"
fi

# ── 4. Transfer ────────────────────────────────────────────────────────────
h "4) Übertragung: iMac → VPS"
scp "$LOCAL_BACKUP" "${VPS_USER}@${VPS_HOST}:/root/backups/imac-hermes-backup-$TS.tar.gz" \
  || { err "Transfer fehlgeschlagen"; exit 1; }
ok "Transfer abgeschlossen"

# ── 5. Merge auf dem VPS ──────────────────────────────────────────────────
h "5) Merge auf dem VPS (iMac-Daten haben Vorrang, nichts wird gelöscht)"
ssh "${VPS_USER}@${VPS_HOST}" bash -s "$CONTAINER" "$TS" "$USE_DOCKER_CP" "$REMOTE_HERMES_PATH" <<'REMOTE_SCRIPT'
set -euo pipefail
CONTAINER="$1"; TS="$2"; USE_DOCKER_CP="$3"; REMOTE_HERMES_PATH="$4"
STAGE="/root/backups/imac-hermes-staged-$TS"
mkdir -p "$STAGE"
tar -xzf "/root/backups/imac-hermes-backup-$TS.tar.gz" -C "$STAGE"

docker stop "$CONTAINER" >/dev/null

if [ "$USE_DOCKER_CP" = "false" ]; then
  mkdir -p "$REMOTE_HERMES_PATH"
  rsync -a "$STAGE/.hermes/" "$REMOTE_HERMES_PATH/"
else
  docker start "$CONTAINER" >/dev/null
  docker cp "$STAGE/.hermes/." "$CONTAINER:/home/hermes/.hermes/"
  docker stop "$CONTAINER" >/dev/null
fi

docker start "$CONTAINER" >/dev/null
echo "MERGE_DONE"
REMOTE_SCRIPT

if [ $? -eq 0 ]; then
  ok "Merge auf VPS abgeschlossen, Container neu gestartet"
else
  err "Merge fehlgeschlagen — VPS-Backup liegt unter /root/backups/vps-hermes-pre-migration-$TS.tar.gz"
  exit 1
fi

# ── 6. Telegram-Token (optional) ──────────────────────────────────────────
h "6) Telegram-Token"
if [ -n "$TELEGRAM_TOKEN" ]; then
  ssh "${VPS_USER}@${VPS_HOST}" \
    "docker exec $CONTAINER sh -c \"sed -i 's|^\([[:space:]]*token:[[:space:]]*\).*|\1\\\"${TELEGRAM_TOKEN}\\\"|' /home/hermes/.hermes/config.yaml\" && docker restart $CONTAINER" \
    && ok "Telegram-Token gesetzt, Container neu gestartet" \
    || warn "Telegram-Token setzen fehlgeschlagen — Feldname im config.yaml prüfen"
else
  warn "Kein TELEGRAM_TOKEN übergeben — übersprungen."
  warn "Nachträglich setzen: TELEGRAM_TOKEN=xxx bash <(curl -fsSL .../hermes-vps-migrate.sh)"
fi

# ── 7. Verifikation ────────────────────────────────────────────────────────
h "7) Verifikation"
sleep 6
echo ""
echo "--- Container Status ---"
ssh "${VPS_USER}@${VPS_HOST}" "docker ps --filter name=$CONTAINER --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""
echo "--- Logs (letzte 15 Zeilen, gefiltert) ---"
ssh "${VPS_USER}@${VPS_HOST}" "docker logs $CONTAINER 2>&1 | grep -iE 'telegram|connected|platform|started|error|skill' | tail -15"

h "FERTIG"
echo ""
echo "📦 Backups (nichts wurde gelöscht):"
echo "   iMac:  $LOCAL_BACKUP"
echo "   VPS:   /root/backups/vps-hermes-pre-migration-$TS.tar.gz"
echo ""
echo "✅ Dein VPS-Hermes hat jetzt deine Konfiguration, Skills, Memories & Sessions."
echo "   Kopiere die Ausgabe oben (Container Status + Logs) an Claude."
