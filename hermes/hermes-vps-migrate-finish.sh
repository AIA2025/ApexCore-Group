#!/bin/bash
# Hermes Desktop → VPS Migration (Abschluss)
# Nutzt ein bereits vorhandenes lokales Backup (~/Desktop/hermes-migration/imac-hermes-backup-*.tar.gz)
# und merged es in den echten Host-Datenpfad /root/.hermes auf dem VPS, der von
# beiden Containern 'hermes' und 'hermes-webui' gemeinsam gemountet wird.
#
# Ausführen (iMac):
#   TELEGRAM_TOKEN=xxx bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/hermes-desktop-troubleshoot-2ynwwu/hermes/hermes-vps-migrate-finish.sh)

set -uo pipefail

VPS_HOST="${VPS_HOST:-76.13.138.73}"
VPS_USER="${VPS_USER:-root}"
CONTAINERS="hermes-webui hermes"
REMOTE_HERMES_PATH="/root/.hermes"
WORKDIR="$HOME/Desktop/hermes-migration"
TS=$(date +%Y%m%d_%H%M%S)
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}▶ $1${NC}"; }

echo -e "${BOLD}╔══════════════════════════════════════════╗"
echo    "║  Hermes Migration — Abschluss            ║"
echo -e "╚══════════════════════════════════════════╝${NC}"

# ── 0. Vorhandenes Backup finden ──────────────────────────────────────────
h "0) Lokales Backup suchen"
LOCAL_BACKUP=$(ls -t "$WORKDIR"/imac-hermes-backup-*.tar.gz 2>/dev/null | head -1)
if [ -z "$LOCAL_BACKUP" ]; then
  err "Kein Backup in $WORKDIR gefunden — bitte zuerst hermes-vps-migrate.sh ausführen"
  exit 1
fi
ok "Backup gefunden: $LOCAL_BACKUP ($(du -h "$LOCAL_BACKUP" | cut -f1))"

ssh -o BatchMode=yes -o ConnectTimeout=8 "${VPS_USER}@${VPS_HOST}" "echo ok" >/dev/null 2>&1 \
  || { err "SSH zum VPS fehlgeschlagen"; exit 1; }
ok "SSH zum VPS funktioniert"

# ── 1. VPS-Backup des bestehenden Zustands ────────────────────────────────
h "1) VPS-Backup von $REMOTE_HERMES_PATH (Sicherheitsnetz)"
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p /root/backups"
ssh "${VPS_USER}@${VPS_HOST}" \
  "tar -czf /root/backups/vps-hermes-pre-migration-$TS.tar.gz -C / root/.hermes" \
  && ok "VPS-Backup erstellt: /root/backups/vps-hermes-pre-migration-$TS.tar.gz" \
  || warn "VPS-Backup fehlgeschlagen (evtl. leerer Ordner) — fahre fort"

# ── 2. Transfer ────────────────────────────────────────────────────────────
h "2) Übertragung: iMac → VPS"
scp "$LOCAL_BACKUP" "${VPS_USER}@${VPS_HOST}:/root/backups/imac-hermes-backup-$TS.tar.gz" \
  || { err "Transfer fehlgeschlagen"; exit 1; }
ok "Transfer abgeschlossen"

# ── 3. Merge (rsync, iMac-Daten haben Vorrang, nichts wird gelöscht) ──────
h "3) Merge in $REMOTE_HERMES_PATH"
ssh "${VPS_USER}@${VPS_HOST}" bash -s "$TS" "$REMOTE_HERMES_PATH" "$CONTAINERS" <<'REMOTE_SCRIPT'
set -euo pipefail
TS="$1"; REMOTE_HERMES_PATH="$2"; CONTAINERS="$3"
STAGE="/root/backups/imac-hermes-staged-$TS"
mkdir -p "$STAGE"
tar -xzf "/root/backups/imac-hermes-backup-$TS.tar.gz" -C "$STAGE"

for c in $CONTAINERS; do docker stop "$c" >/dev/null 2>&1 || true; done

mkdir -p "$REMOTE_HERMES_PATH"
rsync -a "$STAGE/.hermes/" "$REMOTE_HERMES_PATH/"

for c in $CONTAINERS; do docker start "$c" >/dev/null; done
echo "MERGE_DONE"
REMOTE_SCRIPT

if [ $? -eq 0 ]; then
  ok "Merge abgeschlossen, Container neu gestartet"
else
  err "Merge fehlgeschlagen — VPS-Backup liegt unter /root/backups/vps-hermes-pre-migration-$TS.tar.gz"
  exit 1
fi

# ── 4. Telegram-Token (optional, direkt im Host-Pfad) ─────────────────────
h "4) Telegram-Token"
if [ -n "$TELEGRAM_TOKEN" ]; then
  ssh "${VPS_USER}@${VPS_HOST}" bash -s "$REMOTE_HERMES_PATH" "$TELEGRAM_TOKEN" "$CONTAINERS" <<'TOKEN_SCRIPT'
set -euo pipefail
REMOTE_HERMES_PATH="$1"; TOKEN="$2"; CONTAINERS="$3"
CONFIG="$REMOTE_HERMES_PATH/config.yaml"
if [ ! -f "$CONFIG" ]; then
  echo "NO_CONFIG"
  exit 0
fi
FOUND=false
for FIELD in token bot_token api_token telegram_token; do
  if grep -qi "^[[:space:]]*${FIELD}:" "$CONFIG"; then
    sed -i "s|^\([[:space:]]*${FIELD}:[[:space:]]*\).*|\1\"${TOKEN}\"|" "$CONFIG"
    echo "TOKEN_SET:${FIELD}"
    FOUND=true
    break
  fi
done
[ "$FOUND" = false ] && echo "TOKEN_FIELD_NOT_FOUND"
for c in $CONTAINERS; do docker restart "$c" >/dev/null; done
TOKEN_SCRIPT
  ok "Telegram-Token-Update ausgeführt (siehe Ausgabe oben), Container neu gestartet"
else
  warn "Kein TELEGRAM_TOKEN übergeben — übersprungen."
fi

# ── 5. Verifikation ────────────────────────────────────────────────────────
h "5) Verifikation"
sleep 6
for c in $CONTAINERS; do
  echo ""
  echo "--- $c: Status ---"
  ssh "${VPS_USER}@${VPS_HOST}" "docker ps --filter name=$c --format 'table {{.Names}}\t{{.Status}}'"
  echo "--- $c: Logs (gefiltert) ---"
  ssh "${VPS_USER}@${VPS_HOST}" "docker logs $c 2>&1 | grep -iE 'telegram|connected|platform|started|error|skill' | tail -10"
done

h "FERTIG"
echo ""
echo "📦 Backups (nichts wurde gelöscht):"
echo "   iMac:  $LOCAL_BACKUP"
echo "   VPS:   /root/backups/vps-hermes-pre-migration-$TS.tar.gz"
echo ""
echo "✅ Kopiere die Ausgabe oben an Claude zur Kontrolle."
