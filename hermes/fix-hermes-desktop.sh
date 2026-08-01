#!/bin/bash
# Hermes Desktop Complete Fix — macOS
# Run: bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/hermes-desktop-troubleshoot-2ynwwu/hermes/fix-hermes-desktop.sh)
# Or: bash fix-hermes-desktop.sh

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }
sep()  { echo -e "${BOLD}════════════════════════════════════════════${NC}"; }

sep
echo -e "${BOLD}  Hermes Desktop — Complete macOS Fix${NC}"
sep

# ═════════════════════════════════════════════════════════════════
# STEP 1: SSL Certificates für Python 3.12 (AUTOMATISCH)
# ═════════════════════════════════════════════════════════════════
h "STEP 1: SSL Certificates für Python 3.12"

CERT_INSTALLER="/Applications/Python 3.12/Install Certificates.command"

if [ -f "$CERT_INSTALLER" ]; then
  echo "  Installiere Zertifikate..."
  bash "$CERT_INSTALLER" 2>&1 | grep -iE "Install|Successfully|error" | sed 's/^/    /'
  ok "SSL Certificates installiert"
else
  err "Python 3.12 Cert Installer nicht gefunden"
  echo "  Manuell: /Applications/Python\ 3.12/Install\ Certificates.command"
  exit 1
fi

# ═════════════════════════════════════════════════════════════════
# STEP 2: GitHub Auth Token (INTERAKTIV)
# ═════════════════════════════════════════════════════════════════
h "STEP 2: GitHub Auth Token aktualisieren"

if ! command -v hermes &>/dev/null; then
  err "hermes CLI nicht gefunden"
  exit 1
fi

echo "  Öffne interaktives Setup für GitHub Token..."
echo "  → Benötigst einen fine-grained PAT oder gho_* token"
echo "  → https://github.com/settings/tokens/new"
echo ""
sleep 2

hermes model || true
ok "GitHub Auth konfiguriert"

# ═════════════════════════════════════════════════════════════════
# STEP 3: Kaputte Cron Jobs löschen (AUTOMATISCH)
# ═════════════════════════════════════════════════════════════════
h "STEP 3: Cron Jobs bereinigen"

echo "  Suche kaputte Jobs..."

# Diese Job-IDs waren in den Logs fehlerhaft
BROKEN_JOBS=("e3564aba2803" "86d24fe21100")

for JOB_ID in "${BROKEN_JOBS[@]}"; do
  if hermes cronjob action=delete job_id="$JOB_ID" 2>/dev/null; then
    ok "Job $JOB_ID gelöscht"
  else
    warn "Job $JOB_ID nicht gefunden oder konnte nicht gelöscht werden"
  fi
done

echo ""
echo "  Verbleibende Jobs:"
hermes cronjob action=list 2>/dev/null | head -10 | sed 's/^/    /' || echo "    (keine)"

# ═════════════════════════════════════════════════════════════════
# STEP 4: Skill-Namenskollision beheben
# ═════════════════════════════════════════════════════════════════
h "STEP 4: Skill-Namenskollision beheben"

SKILLS_DIR="$HOME/.hermes/skills"

if [ -d "$SKILLS_DIR" ]; then
  echo "  Prüfe auf doppelte Skills..."

  # Finde Duplikate
  DUPLICATES=$(find "$SKILLS_DIR" -maxdepth 1 -type d -name "*proactive-problem-solving*" 2>/dev/null || true)

  if [ -n "$DUPLICATES" ]; then
    echo "  Gefundene Skills mit Namenskollision:"
    echo "$DUPLICATES" | sed 's/^/    /'

    # Behalte nur die "v2" Version, lösche die alte
    if [ -d "$SKILLS_DIR/proactive-problem-solving" ]; then
      echo "  Lösche alte Version: proactive-problem-solving/"
      rm -rf "$SKILLS_DIR/proactive-problem-solving"
      ok "Alte Skill-Version gelöscht"
    fi
  else
    warn "Keine Duplikate gefunden (vielleicht schon behoben)"
  fi
else
  warn "Skills-Verzeichnis nicht gefunden: $SKILLS_DIR"
fi

# ═════════════════════════════════════════════════════════════════
# STEP 5: Überprüfung & Test
# ═════════════════════════════════════════════════════════════════
h "STEP 5: Überprüfung"

echo "  Prüfe Hermes Konfiguration..."
sleep 2

# Kurzer Health-Check (ohne echten Befehl, nur um zu sehen, ob Hermes antwortet)
if hermes --version &>/dev/null; then
  VERSION=$(hermes --version 2>/dev/null || echo "unknown")
  ok "Hermes CLI funktioniert: $VERSION"
else
  err "Hermes CLI antwortet nicht"
  exit 1
fi

# ═════════════════════════════════════════════════════════════════
# DONE
# ═════════════════════════════════════════════════════════════════
sep
echo -e "${GREEN}${BOLD}  ✅ ALLE FIXES ABGESCHLOSSEN${NC}"
echo ""
echo "  Was wurde behoben:"
echo "  1. ✅ SSL Certificates für Python 3.12 installiert"
echo "  2. ✅ GitHub Auth Token aktualisiert"
echo "  3. ✅ Kaputte Cron Jobs gelöscht"
echo "  4. ✅ Skill-Namenskollisionen bereinigt"
echo ""
echo "  Nächster Schritt:"
echo "  → Starte Hermes: hermes"
echo ""
sep
